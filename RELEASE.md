# Release Process

## Major or Minor Releases

1. Create a release branch named `vX.Y.Z` where `X.Y.Z` is the version.
2. Bump version number on release branch.
3. Create an annotated, signed tag: `git tag -s -a vX.Y.Z`
4. Build and publish the package.
5. Bump version number on `main` to the next version followed by `.dev`, e.g. `v0.4.0.dev`.

