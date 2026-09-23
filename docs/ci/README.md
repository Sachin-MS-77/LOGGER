# Docker acceptance workflow template

Local Docker acceptance passed; hosted GitHub Actions has not run. GitHub rejected creation of an active workflow because the saved credential does not have workflow permission.

A repository maintainer can install [docker.yml](docker.yml) as `.github/workflows/docker.yml` using an account or credential authorized to manage workflows. Then run Docker acceptance from the Actions tab and check its result and verification artifact. The template builds the container, checks authenticated ingestion and original bytes, exercises TCP/UDP, and verifies evidence after restart.

Never paste access tokens into project files or chat.
