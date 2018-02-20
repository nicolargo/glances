# How to contribute?

In order to build the assets of the Web UI, you'll need [npm](https://docs.npmjs.com/getting-started/what-is-npm) or [yarn](https://yarnpkg.com).

You must run the following command from the `glances/outputs/static/` directory.

## Install dependencies

You can use yarn or npm:

```bash
$ yarn
```

or:

```bash
$ npm install
```

## Build assets

Run the build command to build assets once :

```bash
$ npm run build
```

or use the watch command to rebuild only modified files :

```bash
$ npm run watch
```

# Anatomy

```bash
static
|
|--- css
|
|--- images
|
|--- js
|
|--- public # path where builds are put
|
|--- templates (bottle)
```

## Data

Each plugin receives the data in the following format:

* stats
* views
* isBsd
* isLinux
* isMac
* isWindows
