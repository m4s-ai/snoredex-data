/* Full-resolution browser decoding and perspective correction for retained gallery recipes. */
async ({ source, recipe, dimensions }) => {
  const image = new Image();
  image.src = source;
  await image.decode();
  if (image.naturalWidth !== recipe.sourceDimensions[0] ||
      image.naturalHeight !== recipe.sourceDimensions[1]) {
    throw new Error("Decoded source dimensions differ from the reviewed recipe");
  }
  const original = document.createElement("canvas");
  original.width = image.naturalWidth;
  original.height = image.naturalHeight;
  const context = original.getContext("2d", { willReadFrequently: true });
  context.drawImage(image, 0, 0);
  const pixels = context.getImageData(0, 0, original.width, original.height).data;
  const [topLeft, topRight, bottomRight, bottomLeft] = recipe.corners;
  const dx1 = topRight[0] - bottomRight[0];
  const dx2 = bottomLeft[0] - bottomRight[0];
  const dx3 = topLeft[0] - topRight[0] + bottomRight[0] - bottomLeft[0];
  const dy1 = topRight[1] - bottomRight[1];
  const dy2 = bottomLeft[1] - bottomRight[1];
  const dy3 = topLeft[1] - topRight[1] + bottomRight[1] - bottomLeft[1];
  const determinant = dx1 * dy2 - dx2 * dy1;
  const g = (dx3 * dy2 - dx2 * dy3) / determinant;
  const h = (dx1 * dy3 - dx3 * dy1) / determinant;
  const ax = topRight[0] - topLeft[0] + g * topRight[0];
  const bx = bottomLeft[0] - topLeft[0] + h * bottomLeft[0];
  const ay = topRight[1] - topLeft[1] + g * topRight[1];
  const by = bottomLeft[1] - topLeft[1] + h * bottomLeft[1];
  const corrected = document.createElement("canvas");
  [corrected.width, corrected.height] = dimensions;
  const correctedContext = corrected.getContext("2d");
  const result = correctedContext.createImageData(...dimensions);
  for (let y = 0; y < corrected.height; y++) {
    for (let x = 0; x < corrected.width; x++) {
      const u = (x + 0.5) / corrected.width;
      const v = (y + 0.5) / corrected.height;
      const divisor = g * u + h * v + 1;
      const sx = Math.max(0, Math.min(original.width - 1,
        (ax * u + bx * v + topLeft[0]) / divisor - 0.5));
      const sy = Math.max(0, Math.min(original.height - 1,
        (ay * u + by * v + topLeft[1]) / divisor - 0.5));
      const left = Math.floor(sx);
      const top = Math.floor(sy);
      const right = Math.min(left + 1, original.width - 1);
      const bottom = Math.min(top + 1, original.height - 1);
      const fx = sx - left;
      const fy = sy - top;
      for (let channel = 0; channel < 4; channel++) {
        const upper = pixels[(top * original.width + left) * 4 + channel] * (1 - fx) +
          pixels[(top * original.width + right) * 4 + channel] * fx;
        const lower = pixels[(bottom * original.width + left) * 4 + channel] * (1 - fx) +
          pixels[(bottom * original.width + right) * 4 + channel] * fx;
        result.data[(y * corrected.width + x) * 4 + channel] = upper * (1 - fy) + lower * fy;
      }
    }
  }
  correctedContext.putImageData(result, 0, 0);
  return [...new Set([240, 480, corrected.width])].sort((a, b) => a - b).map((width) => {
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = Math.floor(width * corrected.height / corrected.width);
    const target = canvas.getContext("2d");
    target.imageSmoothingEnabled = true;
    target.imageSmoothingQuality = "high";
    target.drawImage(corrected, 0, 0, canvas.width, canvas.height);
    return { width: canvas.width, height: canvas.height, data: canvas.toDataURL("image/webp", 0.94) };
  });
}
