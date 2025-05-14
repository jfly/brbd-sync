# A `uv2nix` flake-parts module.
# This is very simple: it currently only supports simple, single package
# workspaces.

{
  lib,
  inputs,
  flake-parts-lib,
  ...
}:

let
  inherit (flake-parts-lib)
    mkPerSystemOption
    ;
in
{
  options = {
    perSystem = mkPerSystemOption {
      options.uv2nix = lib.mkOption {
        description = ''
          Project-level uv2nix configuration.
        '';

        type = lib.types.submodule {
          options = {
            workspaceRoot = lib.mkOption {
              type = lib.types.path;
              description = "Path to the root of the UV workspace";
              apply =
                path:
                # Workaround for https://github.com/pyproject-nix/uv2nix/issues/179
                /. + (builtins.unsafeDiscardStringContext path);
            };

            python = lib.mkOption {
              type = lib.types.package;
              description = "Python package to use";
            };

            pyprojectOverrides = lib.mkOption {
              type = lib.types.raw; # TODO: is there a better type for this?
              description = ''
                Overlays with build fixups.

                See https://pyproject-nix.github.io/uv2nix/usage/hello-world.html?highlight=pyprojectOverrides#flakenix
              '';
              default = _final: _prev: { };
            };

            nativeCheckInputs = lib.mkOption {
              type = lib.types.listOf lib.types.package;
              description = ''
                Additional packages for running tests.
              '';
              default = [ ];
            };

            env = lib.mkOption {
              type = lib.types.attrsOf lib.types.str;
              description = ''
                Build/development environment variables.

                Note: these environment variables are used in the build process
                of *all* local packages for this workspace.
              '';
              default = { };
            };
          };
        };
      };
    };
  };

  config = {
    perSystem =
      {
        config,
        self',
        pkgs,
        ...
      }:
      let
        cfg = config.uv2nix;

        python = cfg.python;

        uv2nix-lib = inputs.uv2nix.lib;

        workspace = uv2nix-lib.workspace.loadWorkspace {
          workspaceRoot = cfg.workspaceRoot;
        };

        pyprojectToml = lib.importTOML (cfg.workspaceRoot + "/pyproject.toml");

        uvLock = uv2nix-lib.lock1.parseLock (lib.importTOML (cfg.workspaceRoot + "/uv.lock"));
        localPackages = builtins.filter uv2nix-lib.lock1.isLocalPackage uvLock.package;

        overlay = workspace.mkPyprojectOverlay {
          sourcePreference = "wheel";
        };
        pythonSet =
          (pkgs.callPackage inputs.pyproject-nix.build.packages {
            inherit python;
          }).overrideScope
            (
              lib.composeManyExtensions [
                inputs.pyproject-build-systems.overlays.default
                overlay
                cfg.pyprojectOverrides
                (
                  final: prev:
                  lib.pipe localPackages [
                    (map (
                      localPackage:
                      lib.nameValuePair localPackage.name (
                        prev.${localPackage.name}.overrideAttrs (oldAttrs: {
                          env = (oldAttrs.env or { }) // cfg.env;
                        })
                      )
                    ))
                    lib.listToAttrs
                  ]
                )
              ]
            );

        # Create an overlay enabling editable mode for all local dependencies.
        editableOverlay = workspace.mkEditablePyprojectOverlay {
          root = "$PRJ_ROOT";
          # TODO: `buttondown-api-client` doesn't work if it's installed
          # editable. Is there some way to mark a project as "not editable
          # compatible", and would uv2nix be able to pick up on that?
          members = [ "brbd-sync" ];
        };

        # Override previous set with our overrideable overlay.
        editablePythonSet = pythonSet.overrideScope (
          lib.composeManyExtensions [
            editableOverlay
          ]
        );

        project = pythonSet.${pyprojectToml.project.name};

        inherit (pkgs.callPackages inputs.pyproject-nix.build.util { }) mkApplication;
      in
      {
        devshells.default =
          let
            # Build virtual environment, with local packages being editable.
            #
            # Enable all optional dependencies for development.
            editableVenv = editablePythonSet.mkVirtualEnv "dev-env" workspace.deps.all;
          in
          {
            packages = [
              editableVenv
              pkgs.uv
            ];

            env = lib.attrsToList (
              {
                # Don't create venv using uv.
                UV_NO_SYNC = "1";

                # Force uv to use Python interpreter from venv.
                UV_PYTHON = "${editableVenv}/bin/python";

                # Prevent uv from downloading managed Pythons.
                UV_PYTHON_DOWNLOADS = "never";
              }
              // cfg.env
            );
          };

        checks = {
          ${project.pname} =
            # Modified from: https://pyproject-nix.github.io/uv2nix/patterns/testing.html#testing
            # We use an editable venv for tests because it makes coverage
            # reporting easier. Without this, you are able to import the project in
            # 2 different ways:
            #
            #   1. Relatively through the `src` directory.
            #   2. In the `site-packages` directory of your python env (this
            #      can happen during "end to end" tests when we run our cli
            #      as a subprocess).
            #
            # It's possible to teach `coverage.py` that multiple paths are
            # actually the same thing [0], but I don't like having multiple
            # copies of the same thing (even if they're identical). An editable
            # venv fixes this issue, so let's use one!
            #
            # [0]: https://coverage.readthedocs.io/en/latest/config.html#config-paths
            let
              # Construct a virtual environment with only the `dev` dependency-group.
              editableVenv = editablePythonSet.mkVirtualEnv "test-env" {
                ${project.pname} = [ "dev" ];
              };
            in
            pkgs.stdenv.mkDerivation {
              name = "${project.pname}-pytest";
              inherit (editablePythonSet.${project.pname}) src;
              nativeBuildInputs = [ editableVenv ] ++ cfg.nativeCheckInputs;

              dontConfigure = true;

              buildPhase = ''
                export PRJ_ROOT=$PWD

                runHook preBuild
                pytest --cov-report term --cov-report html
                runHook postBuild
              '';

              # Install the HTML coverage report into the build output.
              installPhase = ''
                runHook preInstall
                mv htmlcov $out
                runHook postInstall
              '';
            };
        };

        packages.default = self'.packages.${project.pname};
        packages.${project.pname} = mkApplication {
          venv = pythonSet.mkVirtualEnv "application-env" workspace.deps.default;
          package = project;
        };
      };
  };
}
