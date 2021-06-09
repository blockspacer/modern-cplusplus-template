from conans import ConanFile, CMake, tools, AutoToolsBuildEnvironment, RunEnvironment, python_requires
from conans.errors import ConanInvalidConfiguration, ConanException
from conans.tools import os_info
import os, re, stat, fnmatch, platform, glob, traceback, shutil
from functools import total_ordering

# if you using python less than 3 use from distutils import strtobool
from distutils.util import strtobool

ConanRecipeHelper = python_requires('conan_recipe_helper/[*]@blockspacer/testing').cmake()

class {{cookiecutter.project_slug}}Conan(ConanRecipeHelper):
    # The name is CMAKE_PROJECT_NAME.
    name = "{{cookiecutter.project_slug}}"
    # The version is CMAKE_PROJECT_VERSION.
    version = "{{cookiecutter.project_version}}"
    # The homepage is CMAKE_PROJECT_HOMEPAGE_URL.
    # set CMAKE_PROJECT_HOMEPAGE_URL to point to the documentation
    homepage = "{{cookiecutter.project_homepage}}"
    # repository url
    url = "{{cookiecutter.project_url}}"
    topics = ("{{cookiecutter.project_topics}}")
    author = "{{cookiecutter.project_author}}"
    # The description is CMAKE_PROJECT_DESCRIPTION.
    description = ("{{cookiecutter.project_description}}")
    # Indicates license type of the packaged library
    # please use SPDX Identifiers https://spdx.org/licenses/
    license = "{{cookiecutter.project_license}}"

    generators = "cmake", "cmake_paths", "cmake_find_package" , "virtualenv"
    settings = "os", "arch", "compiler", "build_type"

    # Include all of the source files in the exports.
    # If the source code is going to be in the same repo as the Conan recipe,
    # there is no need to define a `source` method.
    exports_sources = ("LICENSE", "VERSION", "*.md", "include/*", "src/*",
                       "cmake/*", "examples/*", "CMakeLists.txt", "tests/*", "benchmarks/*",
                       "scripts/*", "tools/*", "codegen/*", "assets/*",
                       "docs/*", "licenses/*", "patches/*", "resources/*",
                       "submodules/*", "thirdparty/*", "third-party/*",
                       "third_party/*", "{{cookiecutter.project_slug}}/*")

    options = {
        "shared": [True, False],
        "fPIC": [True, False]
    }

    default_options = (
        "shared=True",
        "fPIC": True
    )

    @property
    def _lower_build_type(self):
        return str(self.settings.build_type).lower()

    # config_options() is used to configure or constraint the available options
    # in a package, before they are given a value
    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    # The build_requires attribute lists the dependencies
    # required only when building the package.
    def build_requirements(self):
        self.build_requires("cppcheck_installer/1.90@conan/stable")
        self.build_requires("conan_gtest/stable@conan/stable")

    # The requires attribute lists the dependencies required
    # when using (and building) the package.
    def requirements(self):
        self.requires("entt/3.5.2")

    def _configure_cmake(self):
        # cmake_helper from conan_recipe_helper
        cmake = self.cmake_helper

        cmake.configure(build_folder=self.build_folder)
        return cmake

    # Importing files copies files from the local store to your project.
    def imports(self):
        dest = os.getenv("CONAN_IMPORT_PATH", "bin")
        self.copy("license*", dst=dest, ignore_case=True)
        self.copy("*.dll", dst=dest, src="bin")
        self.copy("*.so", dst=dest, src="bin")
        self.copy("*.dylib*", dst=dest, src="lib")
        self.copy("*.lib*", dst=dest, src="lib")
        self.copy("*.a*", dst=dest, src="lib")
        self.copy("assets", dst=dest, src="assets")

    # builds them according to one ABI, identified by a hash
    # computed by the recipe's package_id() method
    def build(self):
        self.output.info('Building package \'{}\''.format(self.name))

        cmake = self._configure_cmake()

        cpu_count = tools.cpu_count()
        self.output.info('Detected %s CPUs' % (cpu_count))

        # -j flag for parallel builds
        cmake.build(args=["--", "-j%s" % cpu_count])

    def package(self):
        self.output.info('Packaging package \'{}\''.format(self.name))

        cmake = self._configure_cmake()
        cmake.install()

        self.copy("LICENSE", dst="licenses", src=self.source_folder)
        self.copy('*', dst='include', src='{}/include'.format(self.source_folder))

        self.copy(pattern="LICENSE", dst="licenses")
        self.copy('*.cmake', dst='lib', src='{}/lib'.format(self.build_folder), keep_path=True)
        self.copy("*.lib", dst="lib", src="", keep_path=False)
        self.copy("*.a", dst="lib", src="", keep_path=False)
        self.copy("*.lib*", dst="lib", src="", keep_path=False)
        self.copy("*.dll", dst="bin", keep_path=False)
        self.copy("*.so", dst="lib", keep_path=False)
        self.copy("assets", dst="assets", keep_path=False)

    # Add INTERFACE_INCLUDE_DIRECTORIES to cpp_info.includedirs.
    # Add INTERFACE_COMPILE_DEFINITIONS to cpp_info.defines.
    # Add INTERFACE_COMPILE_OPTIONS to cpp_info.cxxflags.[6]
    # Add INTERFACE_LINK_DIRECTORIES to cpp_info.libdirs.
    # Add INTERFACE_LINK_OPTIONS to cpp_info.exelinkflags.[7]
    # For a library target, split LOCATION_<CONFIG> between
    # cpp_info.libdirs (directory prefix) and cpp_info.libs (file suffix).
    # For an executable target, add the directory prefix
    # of LOCATION_<CONFIG> to cpp_info.bindirs.
    def package_info(self):
        self.cpp_info.includedirs = ['{}/include'.format(self.package_folder)]

        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))

        self.env_info.LD_LIBRARY_PATH.append(os.path.join(self.package_folder, "lib"))

        self.cpp_info.libdirs = ["lib"]

        self.cpp_info.bindirs = ["bin"]

        self.cpp_info.libs = tools.collect_libs(self)

        # If we are using CMake, we should install a package configuration file (PCF) regardless,
        # as a best practice, but if we want to let non-CMake projects depend on our Conan package,
        # then we need to fill in cpp_info too.
        self.cpp_info.names["cmake_find_package"] = self.name

        # As of this writing (June 26, 2019), there is no way for a Conan recipe
        # to declare highly granular targets like we can in a PCF.
        # The cmake* family of generators produce a single mega-target
        # representing everything in the package.
        # For this reason, consumers should use the PCF installed
        # by CMake instead of the Find Module (FM) installed by Conan,
        # but for consumers not using CMake, and for packages
        # that really do just export one target,
        # we can make a best effort to fill in cpp_info.
        self.cpp_info.names["cmake_find_package_multi"] = self.name
