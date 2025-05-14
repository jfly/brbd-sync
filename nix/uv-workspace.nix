{ inputs, lib, ... }:
{
  imports = [
    ./uv2nix.nix
    inputs.devshell.flakeModule
  ];

  perSystem =
    { config, pkgs, ... }:
    {
      uv2nix = {
        python = pkgs.python313;

        workspaceRoot = builtins.toString (
          lib.fileset.toSource {
            root = ./..;
            fileset = lib.fileset.unions [
              ../pyproject.toml
              ../uv.lock
              ../src
              ../packages
            ];
          }
        );

        pyprojectOverrides = final: prev: {
          buttondown-api-client = prev.buttondown-api-client.overrideAttrs (oldAttrs: {
            # We need a `$XDG_CACHE_HOME` for `py-generator-build-backend`:
            # <https://github.com/jfly/py-generator-build-backend?tab=readme-ov-file#notes>
            preBuild = ''
              export XDG_CACHE_HOME=$(mktemp -d)
            '';
          });
        };

        env = {
          # See `packages/buttondown-api-client/pyproject.toml`.
          OPENAPI_PYTHON_CLIENT_BIN = lib.getExe pkgs.openapi-python-client;
          BUTTONDOWN_OPENAPI_JSON = builtins.toString inputs.buttondown-openapi;
        };
      };
    };
}
