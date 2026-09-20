// Glances v5 WebUI -- the props AppShell binds on every plugin component.
//
// AppShell renders all plugins through ONE `<component :is>` binding, so it
// passes the same five props to every one of them (AppShell.vue). A component
// that leaves one undeclared does not simply ignore it: Vue turns an
// undeclared prop into a fallthrough ATTRIBUTE, and the DOM then carries
// `server-args="[object Object]"` on that block's root element.
//
// Every plugin therefore declares all five, whether it reads them or not --
// which is why the declaration lives here once instead of being retyped in
// each of the 32 components:
//
//     import { PLUGIN_PROPS } from "./plugin_props.js";
//     export default { name: "PluginX", props: { ...PLUGIN_PROPS } };
//
// Spread, not assigned directly, so a component that needs a sixth prop can
// add it without mutating this shared object.
//
//   payload    the plugin's slice of /api/5/all; null while loading
//   error      the message to render instead of the payload, if any
//   labels     the plugin's schema labels (labels.js), {} when unresolved
//   serverArgs the server's CLI arguments (/api/5/args)
//   degrade    the zone degradation flags in effect (degrade.js)
//
// Cross-cutting values only a handful of plugins read (`rowBudget`,
// `maxProcessesDisplay`, `serverPlugins`) are deliberately NOT here: they
// travel through AppShell's provide()/inject() instead, precisely so they do
// not have to be declared by the plugins that never use them.
export const PLUGIN_PROPS = {
	payload: { type: Object, default: null },
	error: { type: String, default: undefined },
	labels: { type: Object, default: () => ({}) },
	serverArgs: { type: Object, default: () => ({}) },
	degrade: { type: Object, default: () => ({}) },
};
