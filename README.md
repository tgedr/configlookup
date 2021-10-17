# Introduction 
This project aim is to implement a simple and extensible way of accessing configuration. 
The configuration values can be provided in json files, environment variables, secrets, etc.

# Getting Started

## installation
you can install the package from [pypi](https://pypi.org/project/configlookup/):

`pip install configlookup`

## usage
The configuration class is implemented as a singleton.
Main usage:
- define environment vars:
  - CONFIGLOOKUP_ENV - {dev|prod} - default: dev
  - CONFIGLOOKUP_DIR - absolute path where the config json files can be found - default: local dir
  - CONFIGLOOKUP_FILE_PREFIX - prefix of configuration files name - default: configlookup
```
from configlookup.main import Configuration
...
config_value = Configuration.get("root.config_group.key")
```

## rationale
As a singleton, Configuration is loaded when it's called by the first time.
The initialization process can be depicted in the following diagram
```
( read env vars:
  CONFIGLOOKUP_ENV, CONFIGLOOKUP_DIR [D], CONFIGLOOKUP_FILE_PREFIX [P]
) 
=> ( find json files with prefix [P] and with suffixes ["", "_all", "_local"] in [D] ) =>
=> ( process json files by natural order:
  - build a dict structure with all the values,
  - override the value if equivalent key is found in any variable overrider,
    - environment overrider is always the last one to be scanned, so it has higher priority
)
```
Do note the possibility of extending the configuration in runtime, so as an example, 
we can have the following primitive configurations in the json file
```
...
"dev": {
    "server": {
      "password": "gonna-get-it-from-a-new-overrider",
      "user": "gonna-get-it-from-env",
...
```
remember the environment overrider is enabled always, 
and once we enable a secrets overrider, for instance azure keyvault, 
we can read the secret there with key `SERVER--PASSWORD`

...bear in mind the translation of config keys:
- property notation `*.*-*.*` => `*__*_*__*` env var notation
- property notation `*.*-*.*` => `*--*-*--*` key secret notation

## defining config values
### json file
```
{
  "common": {...},
  "dev": {
    "server": {
      "url": "http://www.dev.site.com",
      "resources": {
        "mem": 2048,
        "color": "yellow",
        "mem_min": 1024
      }
  ...
  "prod": {
    "server": {
      "url": "https://www.site.com",
      "resources": {
        "color": "green",
      }
    }
  }
```
The main idea is to define values in the `common` section and then override it accordingly
to the runtime environment, `dev` or `prod`.
The environment is resolved by reading the environment variable `CONFIGLOOKUP_ENV`. 
By default, it assumes `dev`.

In the snippet above if eventually the env var is set:
`CONFIGLOOKUP_ENV=prod` then:

`Configuration.get("server.url")` == `"https://www.site.com"`

...and as a leaf primitive value it can also be obtained by a _var-like_ key:

`Configuration.get("SERVER__URL")` == `"https://www.site.com"`

...the same doesn't happen with 

`Configuration.get("server.url.resources")` == `{"mem": 2048, "color": "green", "mem_min": 1024}`
`Configuration.get("SERVER__URL__RESOURCES")` == `None`

...as it is not a primitive value.


# Build
- check the `helper.sh` script

# Publish
- we publish to pypi, you need to have a pypi account token in `~/.pypirc` to be able to publish it

# Test
- check the `helper.sh` script

# Contribute
- just submit a PR to our [repository](https://github.com/tgedr/configlookup) when you want, we'll look at it
