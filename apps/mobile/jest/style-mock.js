// Jest cannot parse CSS. NativeWind's global.css is compiled by Metro at runtime,
// so tests replace every .css import with an empty module.
module.exports = {};
