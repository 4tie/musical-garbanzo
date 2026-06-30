# AutoQuant Foundation Documentation Index

This document serves as the central index for all Part 01 foundation documentation. It links to and summarizes the core documents that establish AutoQuant's product identity, operating principles, and technical architecture.

## Part 01 Foundation Documents

### 1. PRODUCT_CHARTER.md
**Purpose**: Defines AutoQuant's identity, mission, and owner intent.

**Key Contents**:
- Product name and owner intent (Mohs/Mohsen)
- What AutoQuant is and what it is not
- Core operating rule: AI suggests, backend validates, Freqtrade tests, AutoQuant decides
- Local-only architecture principle
- Main user journey from idea to export
- Final output expectation (.py + .json files)
- Non-negotiable safety rule: no guaranteed profit claims
- Definition of project success

**Core Principle**: AutoQuant is a complete local-only trading strategy validation application for one private user, serving as a serious local strategy lab that helps create, test, improve, validate, and export Freqtrade-compatible trading strategies.

---

### 2. TRADING_DEFINITIONS.md
**Purpose**: Defines the official trading evaluation rules and strategy classification system.

**Key Contents**:
- 20 key trading terms (strategy idea, candidate, profitable backtest, expectancy, Profit Factor, etc.)
- Official profitability logic with 12 required criteria
- 5 classification levels: Rejected, Candidate, Promising, Validated, Approved
- Default threshold examples (configurable by timeframe and risk profile)
- Expectancy formula: (Win Rate × Average Win) - (Loss Rate × Absolute Average Loss)
- Weekly profit targets as high-risk objectives, not promises

**Core Principle**: AutoQuant does not treat one profitable backtest as proof that a strategy is truly profitable. Strategies are judged through measurable evidence, robustness, and risk-aware validation.

---

### 3. AI_PERMISSIONS.md
**Purpose**: Defines the official rulebook for all AI behavior inside AutoQuant.

**Key Contents**:
- 5 AI roles: Assistant, Strategy Designer, Deterministic Code Writer, Repair Agent, Report Writer
- Allowed AI actions (explain, suggest, generate StrategySpec, draft reports, etc.)
- Forbidden AI actions (profit guarantees, fake results, secret leakage, unrestricted code generation, etc.)
- 4 AI action modes: Read-only, Draft, Confirmed Action, Forbidden
- Audit requirements for all AI-assisted write/run actions
- Safety enforcement through technical and process controls

**Core Principle**: AI can explain, suggest, design, and report, but cannot execute, guarantee, or manipulate. The final decision on strategy acceptance always rests with backend validation and Freqtrade results, never with AI judgment alone.

---

### 4. RUN_LIFECYCLE.md
**Purpose**: Defines the complete lifecycle of an AutoQuant run from user input to final decision and export.

**Key Contents**:
- 3 run starting modes: Upload Existing Strategy, Generate New Strategy with AI, Repair Previous Strategy
- 13 official run stages from Setup to Notification
- Detailed requirements for each stage (inputs, actions, outputs, failure handling)
- 13 run states: created, queued, running, waiting_for_confirmation, failed_controlled, failed_system, rejected, candidate, promising, validated, approved, exported, cancelled
- Parent/child run relationships for repair and optimization
- Data availability check with auto-download behavior
- Discord notification integration

**Core Principle**: The run lifecycle provides a structured, comprehensive path from strategy idea to validated export. Each stage has clear purpose, validation criteria, and failure handling. No stage is skipped, and all decisions are backed by data and validation rules.

---

### 5. UI_BLUEPRINT.md
**Purpose**: Provides the complete user interface blueprint for frontend development.

**Key Contents**:
- Global layout: sidebar, top status bar, main content, AI Assistant drawer
- 9 sidebar pages: Dashboard, AutoQuant, Strategy Lab, Optimizer, Runs, Results, Strategy Editor, AI Assistant, Settings
- Detailed page layouts with all sections, components, and interactions
- AutoQuant page with 13 live stage cards
- Visual status rules (green, amber, red, blue, gray)
- Run selector behavior and context updates
- AI Assistant integration and context awareness
- Responsive design and accessibility requirements

**Core Principle**: The UI prioritizes clarity, understandability, and user control throughout the validation lifecycle. Every stage is visible and explainable without requiring raw log analysis. Dark mode, clean cards, and consistent status colors create a professional trading dashboard experience.

---

### 6. QUALITY_RULES.md
**Purpose**: Defines quality standards for the entire AutoQuant project.

**Key Contents**:
- General engineering rules (completeness, modularity, observability, code quality)
- Security and secrets management (no hardcoded tokens, .env usage, UI safety)
- Trading integrity (no fake results, validation rigor, parameter management)
- AI integrity (role boundaries, data usage, safety measures)
- UX quality (user understanding, control, interface design)
- Testing rules (backend, frontend, Freqtrade integration, system integration)
- Documentation quality (code, user, system documentation)
- Performance standards (response time, resource usage, scalability)
- Maintenance standards (code, system, user support)
- Compliance and ethics (trading ethics, data ethics, professional standards)

**Core Principle**: Quality is not an afterthought but a fundamental requirement throughout the development process. Adherence to these rules ensures that the final product meets the owner's requirements for a serious local strategy validation application.

---

### 7. PARTS_ROADMAP.md
**Purpose**: Outlines the complete prompt-pack roadmap for building AutoQuant.

**Key Contents**:
- Part 01: Product Foundation & System Constitution (✅ Complete)
- Part 02: Project Setup From Scratch
- Part 03: Backend Core & Database
- Part 04: Freqtrade Integration
- Part 05: Strategy System
- Part 06: AutoQuant Pipeline
- Part 07: Frontend App Shell & Core Pages
- Part 08: Results, Optimizer, Strategy Editor
- Part 09: AI Assistant & Discord Integration
- Part 10: Errors, Retry History, Backups, and Audit Logs
- Part 11: Testing, Smoke Runs, and Final Local Acceptance

**Core Principle**: The roadmap provides a structured approach to building AutoQuant from foundation to completion, with each part building on the previous and maintaining adherence to the quality rules and architectural principles established in Part 01.

---

## Part 01 Completion Checklist

### Product Foundation ✅
- [x] Product mission defined
- [x] Owner intent documented (Mohs/Mohsen)
- [x] Core operating rule established (AI suggests, backend validates, Freqtrade tests, AutoQuant decides)
- [x] Local-only architecture principle defined
- [x] User journey from idea to export mapped
- [x] Final output expectation specified (.py + .json files)
- [x] Non-negotiable safety rule documented (no guaranteed profit claims)

### Trading Definitions ✅
- [x] 20 key trading terms clearly defined
- [x] Official profitability logic with 12 criteria established
- [x] 5 classification levels defined (Rejected, Candidate, Promising, Validated, Approved)
- [x] Default threshold examples provided (configurable)
- [x] Expectancy formula documented
- [x] Weekly profit targets framed as high-risk objectives
- [x] One backtest is not enough principle established

### AI Permissions ✅
- [x] 5 AI roles defined with clear boundaries
- [x] Allowed AI actions listed
- [x] Forbidden AI actions specified
- [x] 4 AI action modes defined (Read-only, Draft, Confirmed, Forbidden)
- [x] Audit requirements established
- [x] AI as assistant, not final judge principle
- [x] Safety enforcement mechanisms outlined

### Run Lifecycle ✅
- [x] 3 run starting modes defined
- [x] 13 official run stages detailed
- [x] 13 run states specified
- [x] Parent/child run relationships established
- [x] Data availability check with auto-download behavior
- [x] Discord notification integration defined
- [x] Complete workflow from setup to export mapped

### UI Blueprint ✅
- [x] Global layout defined (sidebar, top bar, main content, AI drawer)
- [x] 9 pages/tabs with detailed layouts
- [x] AutoQuant page with 13 live stage cards
- [x] Visual status rules established
- [x] Run selector behavior specified
- [x] AI Assistant integration defined
- [x] Settings pages for all components
- [x] Strategy Editor safety rules documented

### Quality Rules ✅
- [x] General engineering rules established
- [x] Security and secrets management defined
- [x] Trading integrity rules specified
- [x] AI integrity boundaries set
- [x] UX quality standards defined
- [x] Testing requirements outlined
- [x] Documentation quality standards set
- [x] Performance and maintenance standards included

### Roadmap ✅
- [x] Complete 11-part roadmap defined
- [x] Each part with clear objectives and deliverables
- [x] Validation criteria for each part
- [x] Completion criteria for overall project
- [x] Success metrics established

### Implementation Status ✅
- [x] No code implementation started yet
- [x] Ready for Part 02 project setup
- [x] All foundation documentation complete
- [x] Quality rules established for future development
- [x] Clear path forward defined

---

## Summary

Part 01 has successfully established the complete foundation for AutoQuant. All core documents are in place, defining:

1. **Product Identity**: A local-only strategy validation engine for Mohs/Mohsen
2. **Trading Philosophy**: Rigorous, multi-dimensional validation without profit guarantees
3. **AI Boundaries**: AI as assistant within strict safety and permission rules
4. **Process Framework**: Complete run lifecycle from idea to export
5. **User Experience**: Comprehensive UI blueprint for workflow management
6. **Quality Standards**: Engineering, security, trading, AI, UX, and testing rules
7. **Development Path**: Clear 11-part roadmap from setup to final acceptance

The foundation is complete and ready for Part 02: Project Setup From Scratch.
