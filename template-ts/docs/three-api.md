# three.js API signatures, generated from the installed types

**GENERATED — do not edit by hand.** Regenerate with `just api-notes` (it reads
`node_modules/@types/three`, so it is always the version you are compiling against).

- `three` 0.185.1
- `@types/three` 0.185.4

Signatures, not examples. Stale example code drives generated code toward
deprecated APIs; a statement of the current signature does not. If something here
disagrees with `tsc`, `tsc` is right — regenerate this file.

`TGeometry`, `TMaterial`, `TEventMap` and `TTexture` are class type parameters;
they default to the obvious thing and you almost never write them.

Behaviours that are easy to get wrong (readback orientation, colour management,
context limits) are in `docs/three-0.185-notes.md`, not here.

### Renderer and render targets

```ts
new WebGLRenderer(parameters?: WebGLRendererParameters | undefined)
  .setSize(width: number, height: number, updateStyle?: boolean | undefined): void
  .setPixelRatio(value: number): void
  .setClearColor(color: ColorRepresentation, alpha?: number | undefined): void
  .setRenderTarget(renderTarget: WebGLRenderTarget<Texture<unknown, TextureEventMap>> | WebGLRenderTarget<Texture<unknown, TextureEventMap>[]> | null, activeCubeFace?: number | undefined, activeMipmapLevel?: number | undefined): void
  .render(scene: Object3D<Object3DEventMap>, camera: Camera): void
  .readRenderTargetPixels(renderTarget: WebGLRenderTarget<Texture<unknown, TextureEventMap>> | WebGLRenderTarget<Texture<unknown, TextureEventMap>[]>, x: number, y: number, width: number, height: number, buffer: TypedArray, activeCubeFaceIndex?: number | undefined, textureIndex?: number | undefined): void
  .readRenderTargetPixelsAsync(renderTarget: WebGLRenderTarget<Texture<unknown, TextureEventMap>> | WebGLRenderTarget<Texture<unknown, TextureEventMap>[]>, x: number, y: number, width: number, height: number, buffer: TypedArray, activeCubeFaceIndex?: number | undefined, textureIndex?: number | undefined): Promise<TypedArray>
  .setAnimationLoop(callback: XRFrameRequestCallback | null): void
  .dispose(): void
  .forceContextLoss(): void
  .outputColorSpace: string
  .domElement: HTMLCanvasElement
  .autoClear: boolean
  .info: WebGLInfo

new WebGLRenderTarget(width?: number | undefined, height?: number | undefined, options?: RenderTargetOptions | undefined)
  .texture: TTexture
  .setSize(width: number, height: number, depth?: number | undefined): void
  .dispose(): void
  .samples: number
  .depthBuffer: boolean

namespace ColorManagement
  .enabled: boolean
  .workingColorSpace: string

```

### Scene graph

```ts
new Scene()
  .add(object: Object3D<Object3DEventMap>[]): Scene<TEventMap>
  .remove(object: Object3D<Object3DEventMap>[]): Scene<TEventMap>
  .clear(): Scene<TEventMap>
  .background: Color | Texture<unknown, TextureEventMap> | null
  .children: Object3D<Object3DEventMap>[]
  .traverse(callback: (object: Object3D<Object3DEventMap>) => any): void
  .getObjectByName(name: string): Object3D<Object3DEventMap> | undefined

new Object3D()
  .position: Vector3
  .rotation: Euler
  .scale: Vector3
  .quaternion: Quaternion
  .visible: boolean
  .name: string
  .userData: Record<string, any>
  .renderOrder: number
  .add(object: Object3D<Object3DEventMap>[]): Object3D<TEventMap>
  .remove(object: Object3D<Object3DEventMap>[]): Object3D<TEventMap>
  .clear(): Object3D<TEventMap>
  .traverse(callback: (object: Object3D<Object3DEventMap>) => any): void
  .updateMatrixWorld(force?: boolean | undefined): void

new Group()

new Mesh(geometry?: TGeometry | undefined, material?: TMaterial | undefined)
  .geometry: TGeometry
  .material: TMaterial
  .isMesh: true

new InstancedMesh(geometry: TGeometry | undefined, material: TMaterial | undefined, count: number)
  .count: number
  .setMatrixAt(index: number, matrix: Matrix4): InstancedMesh<TGeometry, TMaterial, TEventMap>
  .setColorAt(index: number, color: Color): InstancedMesh<TGeometry, TMaterial, TEventMap>
  .instanceMatrix: InstancedBufferAttribute
  .dispose(): void

```

### Cameras

```ts
new OrthographicCamera(left?: number | undefined, right?: number | undefined, top?: number | undefined, bottom?: number | undefined, near?: number | undefined, far?: number | undefined)
  .left: number
  .right: number
  .top: number
  .bottom: number
  .near: number
  .far: number
  .zoom: number
  .updateProjectionMatrix(): void

new PerspectiveCamera(fov?: number | undefined, aspect?: number | undefined, near?: number | undefined, far?: number | undefined)
  .fov: number
  .aspect: number
  .near: number
  .far: number
  .updateProjectionMatrix(): void

```

### Geometry (2D shapes you will actually use)

```ts
new BufferGeometry()
  .setAttribute(name: K, attribute: Attributes[K]): BufferGeometry<Attributes, TEventMap>
  .getAttribute(name: K): Attributes[K]
  .setIndex(index: BufferAttribute<BufferAttributeEventMap> | number[] | null): BufferGeometry<Attributes, TEventMap>
  .setFromPoints(points: Vector3[] | Vector2[]): BufferGeometry<Attributes, TEventMap>
  .computeBoundingBox(): void
  .translate(x: number, y: number, z: number): BufferGeometry<Attributes, TEventMap>
  .dispose(): void

new BufferAttribute(array: TypedArray, itemSize: number, normalized?: boolean | undefined)
  .array: TypedArray
  .itemSize: number
  .count: number
  .needsUpdate: boolean
  .setXY(index: number, x: number, y: number): BufferAttribute<TEventMap>
  .setXYZ(index: number, x: number, y: number, z: number): BufferAttribute<TEventMap>

new PlaneGeometry(width?: number | undefined, height?: number | undefined, widthSegments?: number | undefined, heightSegments?: number | undefined)
  .parameters: { readonly width: number; readonly height: number; readonly widthSegments: number; readonly heightSegments: number; }

new CircleGeometry(radius?: number | undefined, segments?: number | undefined, thetaStart?: number | undefined, thetaLength?: number | undefined)
  .parameters: { readonly radius: number; readonly segments: number; readonly thetaStart: number; readonly thetaLength: number; }

new RingGeometry(innerRadius?: number | undefined, outerRadius?: number | undefined, thetaSegments?: number | undefined, phiSegments?: number | undefined, thetaStart?: number | undefined, thetaLength?: number | undefined)
  .parameters: { readonly innerRadius: number; readonly outerRadius: number; readonly thetaSegments: number; readonly phiSegments: number; readonly thetaStart: number; readonly thetaLength: number; }

new BoxGeometry(width?: number | undefined, height?: number | undefined, depth?: number | undefined, widthSegments?: number | undefined, heightSegments?: number | undefined, depthSegments?: number | undefined)
  .parameters: { readonly width: number; readonly height: number; readonly depth: number; readonly widthSegments: number; readonly heightSegments: number; readonly depthSegments: number; }

```

### Lines and points

```ts
new Line(geometry?: TGeometry | undefined, material?: TMaterial | undefined)
  .geometry: TGeometry
  .material: TMaterial
  .computeLineDistances(): Line<TGeometry, TMaterial, TEventMap>

new LineSegments(geometry?: TGeometry | undefined, material?: TMaterial | undefined)

new LineLoop(geometry?: TGeometry | undefined, material?: TMaterial | undefined)

new Points(geometry?: TGeometry | undefined, material?: TMaterial | undefined)
  .geometry: TGeometry
  .material: TMaterial

```

### Materials

```ts
new Material()
  .dispose(): void
  .transparent: boolean
  .opacity: number
  .side: Side
  .depthTest: boolean
  .depthWrite: boolean
  .needsUpdate: boolean

new MeshBasicMaterial(parameters?: MeshBasicMaterialParameters | undefined)
  .color: Color
  .map: Texture<unknown, TextureEventMap> | null
  .wireframe: boolean

new LineBasicMaterial(parameters?: LineBasicMaterialParameters | undefined)
  .color: Color
  .linewidth: number

new LineDashedMaterial(parameters?: LineDashedMaterialParameters | undefined)
  .dashSize: number
  .gapSize: number
  .scale: number

new PointsMaterial(parameters?: PointsMaterialParameters | undefined)
  .color: Color
  .size: number
  .sizeAttenuation: boolean

new SpriteMaterial(parameters?: SpriteMaterialParameters | undefined)
  .color: Color
  .map: Texture<unknown, TextureEventMap> | null
  .rotation: number

```

### Math

```ts
new Vector2(x?: number | undefined, y?: number | undefined)
  .set(x: number, y: number): Vector2
  .copy(v: Vector2Like): Vector2
  .clone(): Vector2
  .add(v: Vector2Like): Vector2
  .sub(v: Vector2Like): Vector2
  .multiplyScalar(scalar: number): Vector2
  .length(): number
  .normalize(): Vector2

new Vector3(x?: number | undefined, y?: number | undefined, z?: number | undefined)
  .set(x: number, y: number, z?: number | undefined): Vector3
  .copy(v: Vector3Like): Vector3
  .clone(): Vector3
  .add(v: Vector3Like): Vector3
  .sub(v: Vector3Like): Vector3
  .multiplyScalar(s: number): Vector3
  .length(): number
  .normalize(): Vector3

new Color(color?: ColorRepresentation | undefined)
new Color(r: number, g: number, b: number)
  .set(args: [color: ColorRepresentation] | [r: number, g: number, b: number]): Color
  .setRGB(r: number, g: number, b: number, colorSpace?: string | undefined): Color
  .setHex(hex: number, colorSpace?: string | undefined): Color
  .setStyle(style: string, colorSpace?: string | undefined): Color
  .getHex(colorSpace?: string | undefined): number
  .r: number
  .g: number
  .b: number
  .convertSRGBToLinear(): Color

new Euler(x?: number | undefined, y?: number | undefined, z?: number | undefined, order?: EulerOrder | undefined)
  .set(x: number, y: number, z: number, order?: EulerOrder | undefined): Euler
  .x: number
  .y: number
  .z: number
  .order: EulerOrder

new Quaternion(x?: number | undefined, y?: number | undefined, z?: number | undefined, w?: number | undefined)
  .set(x: number, y: number, z: number, w: number): Quaternion
  .setFromEuler(euler: Euler, update?: boolean | undefined): Quaternion
  .setFromAxisAngle(axis: Vector3Like, angle: number): Quaternion

new Matrix4()
new Matrix4(n11: number, n12: number, n13: number, n14: number, n21: number, n22: number, n23: number, n24: number, n31: number, n32: number, n33: number, n34: number, n41: number, n42: number, n43: number, n44: number)
  .makeTranslation(v: Vector3): Matrix4
  .makeTranslation(x: number, y: number, z: number): Matrix4
  .makeScale(x: number, y: number, z: number): Matrix4
  .compose(position: Vector3, quaternion: Quaternion, scale: Vector3): Matrix4
  .identity(): Matrix4

namespace MathUtils
  .clamp(value: number, min: number, max: number): number
  .lerp(x: number, y: number, t: number): number
  .degToRad(degrees: number): number
  .radToDeg(radians: number): number
  .euclideanModulo(n: number, m: number): number

```

### Textures

```ts
new Texture(image?: TImage | undefined, mapping?: Mapping | undefined, wrapS?: Wrapping | undefined, wrapT?: Wrapping | undefined, magFilter?: MagnificationTextureFilter | undefined, minFilter?: MinificationTextureFilter | undefined, format?: PixelFormat | undefined, type?: TextureDataType | undefined, anisotropy?: number | undefined, colorSpace?: ColorSpace | undefined)
new Texture(image: TImage, mapping: Mapping, wrapS: Wrapping, wrapT: Wrapping, magFilter: MagnificationTextureFilter, minFilter: MinificationTextureFilter, format: PixelFormat, type: TextureDataType, anisotropy: number)
  .needsUpdate: boolean
  .colorSpace: string
  .wrapS: Wrapping
  .wrapT: Wrapping
  .minFilter: MinificationTextureFilter
  .magFilter: MagnificationTextureFilter
  .dispose(): void

new CanvasTexture(canvas?: TCanvas | undefined, mapping?: Mapping | undefined, wrapS?: Wrapping | undefined, wrapT?: Wrapping | undefined, magFilter?: MagnificationTextureFilter | undefined, minFilter?: MinificationTextureFilter | undefined, format?: PixelFormat | undefined, type?: TextureDataType | undefined, anisotropy?: number | undefined)

```

## Not covered here

Anything not in this list is a `rg` away and the installed source is the ground truth:

```
rg "class LineSegments" -A 20 node_modules/@types/three/src/objects/
rg "readRenderTargetPixels" node_modules/@types/three/src/
node -e "console.log(require('three/package.json').version)"
```
