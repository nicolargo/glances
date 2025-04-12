# Focus on the Glances Web User Interface

In order to build the assets of the Web UI, you'll need [NPM](https://docs.npmjs.com/getting-started/what-is-npm).

NPM is a package manager for JavaScript related to [Node.js](https://nodejs.org/en/).

NodeJS should be installed/updated on your system.

## Pre-requisites

### Install NodeJS

Example on Ubuntu OS:

```bash
sudo apt install nodejs npm
```

### Upgrade NodeJS

Example on Ubuntu OS:

```bash
sudo apt update
sudo apt install nodejs npm
sudo npm install -g n
sudo n lts
hash -r
```

## Build Glances WebUI

You must run the following command from the `glances/outputs/static/` directory.

```bash
cd glances/outputs/static/
```

### Install dependencies

```bash
npm ci
```

### Update dependencies

To update all the dependencies to the latest version and package.json and package-lock.json,
you can use the command "npm update --save":

```bash
npm update --save
npx npm-check-updates -u
npm install
```

### Build assets

Run the build command to build assets once :

```bash
npm run build
```

or use the watch command to rebuild only modified files :

```bash
npm run watch
```

## Anatomy

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
|--- templates
```

## Data

Each plugin receives the data in the following format:

* stats
* views
* isBsd
* isLinux
* isMac
* isWindows
