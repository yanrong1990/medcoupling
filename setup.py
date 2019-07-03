import codecs
import glob
import os
import platform
import shutil
import subprocess
import sys
import tarfile
from urllib.request import urlretrieve

from setuptools import find_packages, setup

# Source file to download
MEDCOUPLING_SRC = "http://files.salome-platform.org/Salome/other/medCoupling-9.3.0.tar.gz"

# Environment variables
CMAKE_EXE = os.environ.get("CMAKE_EXE", shutil.which("cmake"))
SWIG_ROOT_DIR = os.environ.get("SWIG_ROOT_DIR")
PYTHON_ROOT_DIR = os.environ.get("PYTHON_ROOT_DIR")
BUILD_TYPE = os.environ.get("BUILD_TYPE")
if BUILD_TYPE is None:
    BUILD_TYPE = "Release"

# Metadata
__author__ = "CEA/DEN, EDF R&D"
__email__ = "webmaster.salome@opencascade.com"
__copyright__ = u"Copyright (c) 2015-2019 {} <{}>".format(__author__, __email__)
__license__ = "License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)"
__version__ = MEDCOUPLING_SRC.partition("medCoupling-")[2].partition(".tar")[0]
__status__ = "Development Status :: 5 - Production/Stable"

basedir = os.path.dirname(os.path.realpath(__file__))
sourcedir_old = os.path.join(basedir, f"MEDCOUPLING-{__version__}")
sourcedir = os.path.join(basedir, f"MEDCOUPLING-{__version__}-src")
configdir = os.path.join(basedir, f"CONFIGURATION_{__version__}")

# Force platform-specific bdist
# https://stackoverflow.com/questions/45150304/how-to-force-a-python-wheel-to-be-platform-specific-when-building-it
try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
    class bdist_wheel(_bdist_wheel):
        def finalize_options(self):
            _bdist_wheel.finalize_options(self)
            self.root_is_pure = False
except ImportError:
    bdist_wheel = None


def read(fname):
    return codecs.open(os.path.join(basedir, fname), encoding="utf-8").read()


def check_os():
    system = platform.system()
    if system == "Darwin":
        print("macOS not yet supported")
        sys.exit(1)


def check_cmake():
    if not CMAKE_EXE:
        print("cmake executable not found. Set CMAKE_EXE environment or update your path")
        sys.exit(1)


def check_swig():
    if not shutil.which("swig"):
        print("swig executable not found. Set SWIG_ROOT_DIR environment or update your path")
        sys.exit(1)


def check_python():
    if not shutil.which("python") and not shutil.which("python3"):
        print("python or python3 executable not found. Set PYTHON_ROOT_DIR environment or update your path")
        sys.exit(1)
    elif sys.version_info.major < 3 or sys.version_info.minor > 6 or sys.version_info.minor < 6:
        print("only python 3.6 is supported")
        sys.exit(1)
    else:
        try:
            import numpy
        except ImportError:
            print("numpy is not installed")
            sys.exit(1)


def patch_MEDCoupling_Swig_Windows(cmakelists):
    with open(cmakelists, "r") as f:
        lines = f.readlines()

    lines.insert(94, '  SET(SWIG_MODULE_MEDCouplingCompat_EXTRA_FLAGS "${NUMPY_DEFINITIONS};${SCIPY_DEFINITIONS}")\n')
    with open(cmakelists, "w") as f:
        f.writelines(lines)


# Download source files
if not os.path.isdir(sourcedir):
    print(f"Downloading {MEDCOUPLING_SRC}...")
    filename, _ = urlretrieve(MEDCOUPLING_SRC)
    src = tarfile.open(filename)
    print(f"Extracting...")
    src.extractall()
    os.rename(sourcedir_old, sourcedir)

    # Apply patch for Windows
    if platform.system() == "Windows":
        print(f"Applying patch for Windows...")
        cmakelists = os.path.join(sourcedir, "src", "MEDCoupling_Swig", "CMakeLists.txt")
        if not os.path.isfile(cmakelists):
            print(f"Unable to find {cmakelists}")
            sys.exit(1)
        patch_MEDCoupling_Swig_Windows(cmakelists)

# Building
check_os()
check_cmake()
check_swig()
check_python()

builddir = os.path.join(sourcedir, "build")
os.makedirs(builddir, exist_ok=True)

cmake_args = [CMAKE_EXE, sourcedir,
              f"-DCONFIGURATION_ROOT_DIR={configdir}",
              f"-DCMAKE_INSTALL_PREFIX=install",
              "-DMEDCOUPLING_MICROMED=ON",
              "-DMEDCOUPLING_BUILD_DOC=OFF",
              "-DMEDCOUPLING_ENABLE_PARTITIONER=OFF",
              "-DMEDCOUPLING_BUILD_TESTS=OFF",
              "-DMEDCOUPLING_ENABLE_RENUMBER=OFF",
              "-DMEDCOUPLING_WITH_FILE_EXAMPLES=OFF"
              "-DCMAKE_BUILD_TYPE=" + BUILD_TYPE]
if PYTHON_ROOT_DIR is not None:
    cmake_args += [f"-DPYTHON_ROOT_DIR={PYTHON_ROOT_DIR}"]
if SWIG_ROOT_DIR is not None:
    cmake_args += [f"-DSWIG_ROOT_DIR={SWIG_ROOT_DIR}"]

env = os.environ.copy()
subprocess.check_call(cmake_args, cwd=builddir, env=env)

cmake_build_args = [CMAKE_EXE, "--build", ".", "--config", BUILD_TYPE, "--target", "install"]
subprocess.check_call(cmake_build_args, cwd=builddir, env=env)

print(f"Copying C++/Python libary files...")
installdir = os.path.join(basedir, "medcoupling")
lib_dir = os.path.join(builddir, "install", "lib")
for f in glob.glob(os.path.join(lib_dir, "*.dll")):
    shutil.move(f, installdir)

python_dir = os.path.join(lib_dir, "python3.6", "site-packages")
for f in glob.glob(os.path.join(python_dir, "*.py*")):
    shutil.move(f, installdir)
for f in glob.glob(os.path.join(python_dir, "*.so")):
    shutil.move(f, installdir)


setup(
    name="medcoupling",
    version=__version__,
    packages=find_packages(),
    package_data={"": ["*.dll", "*.so", "*.pyd"]},
    url="https://docs.salome-platform.org/latest/dev/MEDCoupling/developer/index.html",
    author=__author__,
    author_email=__email__,
    description="The MEDCoupling tool gathers several powerful functionalities around the input and output data of simulation codes (meshes and fields mainly).",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    license=__license__,
    classifiers=[
        __license__,
        __status__,
        # See <https://pypi.org/classifiers/> for all classifiers.
        "Operating System :: Microsoft :: Windows",
        "Operating System :: Unix",
        "Programming Language :: Python :: 3.6",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Physics",
    ],
    cmdclass={"bdist_wheel": bdist_wheel},
)
