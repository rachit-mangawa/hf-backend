import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

const SIZES = [
  { name: 'favicon-16x16.png', size: 16 },
  { name: 'favicon-32x32.png', size: 32 },
  { name: 'favicon-48x48.png', size: 48 },
  { name: 'apple-touch-icon.png', size: 180 },
  { name: 'android-chrome-192x192.png', size: 192 },
  { name: 'android-chrome-512x512.png', size: 512 },
];

const SVG_PATH = path.resolve('frontend/favicon.svg');
const OUT_DIR = path.resolve('frontend');

console.log('Rendering raster PNGs from favicon.svg...');
for (const { name, size } of SIZES) {
  const dest = path.join(OUT_DIR, name);
  console.log(`Generating ${name} (${size}x${size})...`);
  execSync(`npx -y @resvg/resvg-js-cli --fit-width ${size} --fit-height ${size} "${SVG_PATH}" "${dest}"`, { stdio: 'inherit' });
}

console.log('Packing 16, 32, 48 PNGs into favicon.ico...');
// Create ICO file format containing 16x16, 32x32, 48x48 PNGs
const icoSizes = [16, 32, 48];
const images = icoSizes.map(sz => {
  const filePath = path.join(OUT_DIR, `favicon-${sz}x${sz}.png`);
  const buf = fs.readFileSync(filePath);
  return { size: sz, data: buf };
});

const numImages = images.length;
const headerLen = 6;
const dirEntryLen = 16;
let currentOffset = headerLen + dirEntryLen * numImages;

const header = Buffer.alloc(6);
header.writeUInt16LE(0, 0); // Reserved
header.writeUInt16LE(1, 2); // Type 1 = ICO
header.writeUInt16LE(numImages, 4); // Count

const dirEntries = [];
for (const img of images) {
  const entry = Buffer.alloc(16);
  entry.writeUInt8(img.size >= 256 ? 0 : img.size, 0); // Width
  entry.writeUInt8(img.size >= 256 ? 0 : img.size, 1); // Height
  entry.writeUInt8(0, 2); // Color palette
  entry.writeUInt8(0, 3); // Reserved
  entry.writeUInt16LE(1, 4); // Color planes
  entry.writeUInt16LE(32, 6); // Bits per pixel
  entry.writeUInt32LE(img.data.length, 8); // Image size in bytes
  entry.writeUInt32LE(currentOffset, 12); // Offset of image data
  dirEntries.push(entry);
  currentOffset += img.data.length;
}

const icoBuffer = Buffer.concat([
  header,
  ...dirEntries,
  ...images.map(img => img.data)
]);

fs.writeFileSync(path.join(OUT_DIR, 'favicon.ico'), icoBuffer);
fs.writeFileSync(path.resolve('favicon.ico'), icoBuffer);
console.log('Successfully generated frontend/favicon.ico and root favicon.ico!');

