import eslint from "@eslint/js";
import eslintConfigPrettier from "eslint-config-prettier";
import eslintPluginVue from "eslint-plugin-vue";
import globals from "globals";
import typescriptEslint from "typescript-eslint";

export default typescriptEslint.config(
	{ ignores: ["*.d.ts", "**/coverage", "**/dist"] },
	{
		extends: [
			eslint.configs.recommended,
			...typescriptEslint.configs.recommended,
			...eslintPluginVue.configs["flat/recommended"],
		],
		files: ["**/*.{ts,vue}"],
		languageOptions: {
			ecmaVersion: "latest",
			sourceType: "module",
			globals: globals.browser,
			parserOptions: {
				parser: typescriptEslint.parser,
			},
		},
		rules: {
			// your rules
		},
	},
	// The WebUI's pure JS modules. Their own block on purpose: widening
	// the glob above to plain `.js` would drag this file and
	// webpack.config.js into the lint set.
	{
		extends: [eslint.configs.recommended],
		files: ["**/js/**/*.js"],
		languageOptions: {
			ecmaVersion: "latest",
			sourceType: "module",
			globals: globals.browser,
		},
	},
	// The node --test suites that exercise those modules (tests/js/*.mjs).
	// They sit outside this directory, and ESLint 10 refuses files above the
	// config's base path. Confirmed working invocation: run from the
	// repository root with an explicit --config.
	//
	//   glances/outputs/static/node_modules/.bin/eslint \
	//     --config glances/outputs/static/eslint.config.mjs \
	//     glances/outputs/static/js tests/js
	//
	// Hence the leading `**/` on both globs above and below: it matches zero
	// directories too, so the same patterns hold from either directory.
	{
		extends: [eslint.configs.recommended],
		files: ["**/tests/js/**/*.mjs"],
		languageOptions: {
			ecmaVersion: "latest",
			sourceType: "module",
			globals: globals.node,
		},
	},
	eslintConfigPrettier,
);
