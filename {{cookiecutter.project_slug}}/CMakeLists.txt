cmake_minimum_required(VERSION 3.15)
project({{cookiecutter.project_slug}} CXX)

conan(
    # PACKAGES
)

add_subdirectory(src)
