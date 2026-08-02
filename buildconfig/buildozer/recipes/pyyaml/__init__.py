from pythonforandroid.recipe import PythonRecipe


class PyYAMLRecipe(PythonRecipe):
    version = "6.0.2"
    url = "https://github.com/yaml/pyyaml/archive/refs/tags/{version}.tar.gz"
    site_packages_name = "yaml"
    call_hostpython_via_targetpython = False
    install_in_hostpython = True

    def get_recipe_env(self, arch=None, with_flags_in_cc=True):
        env = super().get_recipe_env(
            arch,
            with_flags_in_cc=with_flags_in_cc,
        )

        # Force the pure-Python PyYAML installation.
        # The optional LibYAML extension is not needed by Tuxemon.
        env["PYYAML_FORCE_CYTHON"] = "0"
        env["PYYAML_FORCE_LIBYAML"] = "0"

        return env


recipe = PyYAMLRecipe()
