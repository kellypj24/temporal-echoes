# UI Module Rules

Pygame rendering, sprites, UI components. **No game logic allowed.**

## Rules
- This module is VIEW only. Never modify game state here.
- All renderables implement: `render(surface, camera_x, camera_y)`
- Layer-based rendering order: BACKGROUND -> TILES_GROUND -> TILES_OBJECTS -> ENTITIES -> TILES_OVERHEAD -> UI -> DEBUG
- Cache sprites on load (SpriteCache). Never load assets during render loop.
- Only render objects in viewport (viewport culling).
- Clear renderable lists after each frame.
- 60 FPS target: frame time < 16ms.
- Pixel-perfect alignment, no sub-pixel positioning (16-bit aesthetic).
- Tile size: 32x32. Character sprites: 32x32 to 48x48.

## Anti-Patterns
- Game logic in rendering code
- Loading assets during render loop
- Creating new surfaces each frame
- Rendering off-screen objects
- Modifying game state from render methods

## Reference
Full patterns: `.cursor/rules/pygame-worker.mdc`
