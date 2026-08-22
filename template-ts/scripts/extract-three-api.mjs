/**
 * Regenerates `docs/three-api.md` from the INSTALLED `@types/three`.
 *
 * WHY THIS EXISTS: a hand-written API note goes stale the moment three is
 * upgraded, and a stale note is worse than none — it is confidently wrong. This
 * reads the type checker, so the document is always the version in
 * `node_modules`. Run `just api-notes` after any three upgrade.
 *
 * It prints SIGNATURES, not example code, on purpose: worked examples that
 * predate the installed version pull generated code back toward deprecated
 * APIs, while a plain statement of the current signature does not.
 *
 *     node scripts/extract-three-api.mjs > docs/three-api.md
 */
import ts from 'typescript';
import { writeFileSync, unlinkSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const ROOT = fileURLToPath(new URL('..', import.meta.url));

const GROUPS = {
  'Renderer and render targets': ['WebGLRenderer', 'WebGLRenderTarget', 'ColorManagement'],
  'Scene graph': ['Scene', 'Object3D', 'Group', 'Mesh', 'InstancedMesh'],
  Cameras: ['OrthographicCamera', 'PerspectiveCamera'],
  'Geometry (2D shapes you will actually use)': [
    'BufferGeometry',
    'BufferAttribute',
    'PlaneGeometry',
    'CircleGeometry',
    'RingGeometry',
    'BoxGeometry',
  ],
  'Lines and points': ['Line', 'LineSegments', 'LineLoop', 'Points'],
  Materials: [
    'Material',
    'MeshBasicMaterial',
    'LineBasicMaterial',
    'LineDashedMaterial',
    'PointsMaterial',
    'SpriteMaterial',
  ],
  Math: ['Vector2', 'Vector3', 'Color', 'Euler', 'Quaternion', 'Matrix4', 'MathUtils'],
  Textures: ['Texture', 'CanvasTexture'],
};

const MEMBERS = {
  WebGLRenderer: [
    'setSize',
    'setPixelRatio',
    'setClearColor',
    'setRenderTarget',
    'render',
    'readRenderTargetPixels',
    'readRenderTargetPixelsAsync',
    'setAnimationLoop',
    'dispose',
    'forceContextLoss',
    'outputColorSpace',
    'domElement',
    'autoClear',
    'info',
  ],
  WebGLRenderTarget: ['texture', 'setSize', 'dispose', 'samples', 'depthBuffer'],
  ColorManagement: ['enabled', 'workingColorSpace'],
  Scene: ['add', 'remove', 'clear', 'background', 'children', 'traverse', 'getObjectByName'],
  Object3D: [
    'position',
    'rotation',
    'scale',
    'quaternion',
    'visible',
    'name',
    'userData',
    'renderOrder',
    'add',
    'remove',
    'clear',
    'traverse',
    'updateMatrixWorld',
  ],
  Group: [],
  Mesh: ['geometry', 'material', 'isMesh'],
  InstancedMesh: ['count', 'setMatrixAt', 'setColorAt', 'instanceMatrix', 'dispose'],
  OrthographicCamera: [
    'left',
    'right',
    'top',
    'bottom',
    'near',
    'far',
    'zoom',
    'updateProjectionMatrix',
  ],
  PerspectiveCamera: ['fov', 'aspect', 'near', 'far', 'updateProjectionMatrix'],
  BufferGeometry: [
    'setAttribute',
    'getAttribute',
    'setIndex',
    'setFromPoints',
    'computeBoundingBox',
    'translate',
    'dispose',
  ],
  BufferAttribute: ['array', 'itemSize', 'count', 'needsUpdate', 'setXY', 'setXYZ'],
  PlaneGeometry: ['parameters'],
  CircleGeometry: ['parameters'],
  RingGeometry: ['parameters'],
  BoxGeometry: ['parameters'],
  Line: ['geometry', 'material', 'computeLineDistances'],
  LineSegments: [],
  LineLoop: [],
  Points: ['geometry', 'material'],
  Material: ['dispose', 'transparent', 'opacity', 'side', 'depthTest', 'depthWrite', 'needsUpdate'],
  MeshBasicMaterial: ['color', 'map', 'wireframe'],
  LineBasicMaterial: ['color', 'linewidth'],
  LineDashedMaterial: ['dashSize', 'gapSize', 'scale'],
  PointsMaterial: ['color', 'size', 'sizeAttenuation'],
  SpriteMaterial: ['color', 'map', 'rotation'],
  Vector2: ['set', 'copy', 'clone', 'add', 'sub', 'multiplyScalar', 'length', 'normalize'],
  Vector3: ['set', 'copy', 'clone', 'add', 'sub', 'multiplyScalar', 'length', 'normalize'],
  Color: ['set', 'setRGB', 'setHex', 'setStyle', 'getHex', 'r', 'g', 'b', 'convertSRGBToLinear'],
  Euler: ['set', 'x', 'y', 'z', 'order'],
  Quaternion: ['set', 'setFromEuler', 'setFromAxisAngle'],
  Matrix4: ['makeTranslation', 'makeScale', 'compose', 'identity'],
  MathUtils: ['clamp', 'lerp', 'degToRad', 'radToDeg', 'euclideanModulo'],
  Texture: ['needsUpdate', 'colorSpace', 'wrapS', 'wrapT', 'minFilter', 'magFilter', 'dispose'],
  CanvasTexture: [],
};

const version = JSON.parse(
  ts.sys.readFile(`${ROOT}node_modules/@types/three/package.json`) ?? '{}',
).version;

const HEADER = `# three.js API signatures, generated from the installed types

**GENERATED — do not edit by hand.** Regenerate with \`just api-notes\` (it reads
\`node_modules/@types/three\`, so it is always the version you are compiling against).

- \`three\` ${JSON.parse(ts.sys.readFile(`${ROOT}node_modules/three/package.json`) ?? '{}').version}
- \`@types/three\` ${version}

Signatures, not examples. Stale example code drives generated code toward
deprecated APIs; a statement of the current signature does not. If something here
disagrees with \`tsc\`, \`tsc\` is right — regenerate this file.

\`TGeometry\`, \`TMaterial\`, \`TEventMap\` and \`TTexture\` are class type parameters;
they default to the obvious thing and you almost never write them.

Behaviours that are easy to get wrong (readback orientation, colour management,
context limits) are in \`docs/three-0.185-notes.md\`, not here.
`;

const FOOTER = `## Not covered here

Anything not in this list is a \`rg\` away and the installed source is the ground truth:

\`\`\`
rg "class LineSegments" -A 20 node_modules/@types/three/src/objects/
rg "readRenderTargetPixels" node_modules/@types/three/src/
node -e "console.log(require('three/package.json').version)"
\`\`\`
`;

const probe = `${ROOT}__sigprobe.ts`;
writeFileSync(probe, `import * as THREE from 'three';\nexport type T = typeof THREE;\n`);

const config = ts.parseJsonConfigFileContent(
  ts.readConfigFile(`${ROOT}tsconfig.json`, ts.sys.readFile).config,
  ts.sys,
  ROOT,
);
const program = ts.createProgram([probe], { ...config.options, noEmit: true });
const checker = program.getTypeChecker();
const source = program.getSourceFile(probe);
const alias = checker.getSymbolAtLocation(source.statements[0].importClause.namedBindings.name);
const ns = checker.getExportsOfModule(checker.getAliasedSymbol(alias));
const byName = new Map(ns.map((s) => [s.name, s]));

const fmt = (t) =>
  checker
    .typeToString(
      t,
      undefined,
      ts.TypeFormatFlags.NoTruncation | ts.TypeFormatFlags.UseFullyQualifiedType,
    )
    .replace(/\bimport\("[^"]*"\)\./g, '');

const lines = [];
for (const [group, names] of Object.entries(GROUPS)) {
  lines.push(`### ${group}\n`);
  lines.push('```ts');
  for (const name of names) {
    const symbol = byName.get(name);
    if (symbol === undefined) {
      lines.push(`// ${name}: NOT EXPORTED by three 0.185.1`);
      continue;
    }
    const staticType = checker.getTypeOfSymbolAtLocation(symbol, symbol.valueDeclaration ?? source);
    const ctors = staticType.getConstructSignatures();
    if (ctors.length === 0) {
      lines.push(`namespace ${name}`);
    }
    for (const ctor of ctors) {
      const params = ctor
        .getParameters()
        .map((p) => {
          const decl = p.valueDeclaration;
          const optional = decl?.questionToken !== undefined ? '?' : '';
          return `${p.name}${optional}: ${fmt(checker.getTypeOfSymbolAtLocation(p, decl ?? source))}`;
        })
        .join(', ');
      lines.push(`new ${name}(${params})`);
    }
    const instance = ctors[0]
      ? ctors[0].getReturnType()
      : checker.getTypeOfSymbolAtLocation(symbol, symbol.valueDeclaration ?? source);
    for (const member of MEMBERS[name] ?? []) {
      const prop = instance.getProperty(member) ?? staticType.getProperty(member);
      if (prop === undefined) {
        lines.push(`  // .${member} — NOT PRESENT in 0.185.1`);
        continue;
      }
      const decl = prop.valueDeclaration ?? prop.declarations?.[0];
      const type = checker.getTypeOfSymbolAtLocation(prop, decl ?? source);
      const calls = type.getCallSignatures();
      if (calls.length > 0) {
        for (const call of calls) {
          const params = call
            .getParameters()
            .map((p) => {
              const d = p.valueDeclaration;
              const optional = d?.questionToken !== undefined ? '?' : '';
              return `${p.name}${optional}: ${fmt(checker.getTypeOfSymbolAtLocation(p, d ?? source))}`;
            })
            .join(', ');
          lines.push(`  .${member}(${params}): ${fmt(call.getReturnType())}`);
        }
      } else {
        lines.push(`  .${member}: ${fmt(type)}`);
      }
    }
    lines.push('');
  }
  lines.push('```\n');
}
unlinkSync(probe);

console.log(HEADER);
console.log(lines.join('\n'));
console.log(FOOTER);
