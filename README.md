# Glances website

## Installation

Install Bower :
```
npm install -g bower
```

Install Brunch :
```
npm install -g brunch
```

Install npm dependencies :
```
npm install
```

Install bower dependencies :
```
bower install
```

## Usage

All development assets files are in the `app` directory and are automatically built/copied into `public` directory by Brunch.

Run the following command before starting to code :
```
brunch watch
```

Or run this one for one shot build :
```
brunch build
```

## How to contribute ?

In order to optimize css and js files for production, always run the following command before push :

```
brunch build -P
```
