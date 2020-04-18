with import <nixpkgs> {};

let
  pname   = "gc-predictor-algo";
  version = "0.0.1";
  project-python-packages = python-packages: with python-packages; [
    pandas
    scikitlearn
    numpy
    joblib
    jupyter
    jupyterlab
    notebook
    matplotlib
    seaborn
    statsmodels
    jsonschema
    tqdm
  ];
  python-with-packages = python3.withPackages project-python-packages;
in
clangStdenv.mkDerivation rec {
  name = pname;
  src = if lib.inNixShell then null else ./.;

  nativeBuildInputs = [
    stdenv
  ];

  buildInputs = [
    python-with-packages
  ];

  # prebuild               = ''
  #   ninja clean
  # '';

  # buildPhase             = ''
  #   ninja
  # '';

  outputs = [ "out" ];
  
  makeTarget             = "gc-predictor-algo";
  enableParallelBuilding = true;

  doCheck                = false;
  checkTarget            = "test";

  installPhase           = ''

  '';
}
