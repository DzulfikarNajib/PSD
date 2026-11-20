# AutoMatch — Agent Guidelines & Anti-Slop Configuration

<!-- antislop:start -->
You use **antislop** (Anti Slop: Rules for AI Coding Agents). It is a filter, not a style guide: it stops generic AI slop in generated UI, copy, and code, without prescribing aesthetics.

For UI, copy, accessibility, mobile layout, or code comments work, load the matching antislop skill before starting:
- **Core filter (always on)**: `.agents/skills/antislop/SKILL.md`
- **UI / visual craft**: `.agents/skills/antislop-ui/SKILL.md`
- **Copy & text tone**: `.agents/skills/antislop-copywriting/SKILL.md`
- **Human / accessibility**: `.agents/skills/antislop-human/SKILL.md`
- **Mobile / responsive layout**: `.agents/skills/antislop-layoutmobile/SKILL.md`
- **Code comments & clean code**: `.agents/skills/antislop-code/SKILL.md`

### Design Direction & Aesthetics
Anti-slop rejects slop, but it never invents aesthetic direction. Visual direction, tokens, branding, and layouts are defined strictly in:
- `DESIGN.md` (Design system, typography, colors, layout proportions)
- `assets/` (Official logo and hero assets)
<!-- antislop:end -->
