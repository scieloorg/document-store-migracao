# Migration Tool

It is a tool specifically built to migrate your SciELO collection to a new platform named SciELO Publishing Framework. Those next topics must contain more information about the way to operate this engine.

### FAQ

- **Q**: During the conversion step the Python process crash.
  - **A1**: If you are using the macOS system and any version of python below than 3.8, please try to execute this `export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES` then try to execute the conversion step again.
  - **A2**: This step requires an internet connection so please verify your internet connection before running the conversion step.