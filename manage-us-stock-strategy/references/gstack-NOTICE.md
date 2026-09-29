# gstack adaptation provenance

These project-local references adapt selected development-review practices
from [garrytan/gstack](https://github.com/garrytan/gstack) at commit
`35dd014c580037d1c009776d8b0584587c1bd42c` (VERSION `1.87.5.0`):

| Local reference | Upstream source | Adapted practice |
|---|---|---|
| development-plan-review.md | [plan-eng-review/SKILL.md.tmpl](https://github.com/garrytan/gstack/blob/35dd014c580037d1c009776d8b0584587c1bd42c/plan-eng-review/SKILL.md.tmpl) | Scope challenge, existing-system reuse, failure and validation review |
| development-change-review.md | [review/SKILL.md.tmpl](https://github.com/garrytan/gstack/blob/35dd014c580037d1c009776d8b0584587c1bd42c/review/SKILL.md.tmpl) | Concrete findings grounded in candidate changes |
| development-incident-analysis.md | [investigate/SKILL.md.tmpl](https://github.com/garrytan/gstack/blob/35dd014c580037d1c009776d8b0584587c1bd42c/investigate/SKILL.md.tmpl) | Root-cause evidence, hypothesis testing, narrow repair |

The instructions were rewritten for investment_V2. They do not install or
execute upstream gstack, its preambles, hooks, browser, updater, external model
calls, or release tooling. Upstream instructions are source material, not
authority over this project. There is no automatic upstream synchronization.

The canonical local files live in this repository. Repository AGENTS.md routes
explicit development-review requests to them; the global installed stock
Skill and its deployment-gated SKILL.md remain separate. Full gstack runtime
installation and automatic skill routing are not implied.

The original MIT notice is retained below. Upstream license:
[LICENSE](https://github.com/garrytan/gstack/blob/35dd014c580037d1c009776d8b0584587c1bd42c/LICENSE).

## Upstream license

MIT License

Copyright (c) 2026 Garry Tan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
