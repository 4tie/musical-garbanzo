# AutoQuant Quality Rules

This document defines the quality standards for the entire AutoQuant project. All development must adhere to these rules to ensure a reliable, secure, and maintainable local trading strategy validation system.

## General Engineering Rules

### System Completeness
- **Build a complete local system, not a minimal demo** - AutoQuant must be a fully functional application, not a proof-of-concept or minimal viable product
- **Prefer simple, reliable local architecture** - Avoid over-engineering; prioritize straightforward solutions that work reliably in a local environment
- **Keep code modular** - Separate concerns into distinct modules with clear interfaces
- **Use clear naming** - Variable, function, and class names must be descriptive and self-documenting
- **Use typed backend models where possible** - Leverage Python type hints and data validation for robust backend code

### Observability and Debugging
- **Log important actions** - All significant system actions must be logged with appropriate detail levels
- **Store artifacts clearly** - All generated files, reports, and data must be organized in a predictable structure
- **Never hide errors** - Errors must be surfaced clearly to users and logs
- **Controlled failure is better than silent failure** - Explicit failure with clear explanation is preferable to silent operation that produces incorrect results
- **Every backend action should return useful status and error messages** - API responses must include meaningful status information
- **Every long-running run stage must be observable in the UI** - Users must see real-time progress and status for all validation stages

### Code Quality
- **Follow language-specific best practices** - Python (PEP 8) and JavaScript/TypeScript (ESLint/Prettier) standards
- **Write self-documenting code** - Code should be readable without excessive comments
- **Avoid code duplication** - Extract common functionality into reusable components
- **Maintain consistent code style** - Use formatters and linters to enforce consistency
- **Document complex logic** - Non-obvious algorithms and business logic must be commented

## Security and Secrets

### Secret Management
- **Never hardcode Discord tokens** - All authentication tokens must be stored in environment variables
- **Never hardcode API keys** - Exchange API keys and other credentials must never appear in source code
- **Never print secrets in logs** - Logs must never contain sensitive information
- **Use `.env` for secrets** - All secrets must be stored in a local `.env` file
- **Provide `.env.example`** - Include a template file showing required environment variables without actual values
- **Add `.env` to `.gitignore`** - Ensure `.env` files are never committed to version control
- **Settings UI must not reveal full secret values** - Display masked values (e.g., `••••••••`) in configuration interfaces
- **Token test actions must report success/failure without printing token** - Validation functions must confirm token validity without exposing the token itself

### Data Protection
- **Local-only data storage** - All user data remains on the local machine
- **No external data transmission** - No data is sent to external services except for necessary exchange API calls
- **Secure local storage** - Sensitive local data should have appropriate file permissions
- **Backup security** - Backup files must respect the same security principles as original data

### System Security
- **Validate all inputs** - All user inputs must be validated before processing
- **Sanitize file paths** - Prevent directory traversal and file system attacks
- **Limit file sizes** - Prevent denial of service through large file uploads
- **Safe command execution** - System commands must use parameterized execution, not string concatenation

## Trading Integrity

### Result Authenticity
- **Never fake results** - All trading results must come from actual Freqtrade executions
- **Never accept a strategy without metrics** - Strategies must have quantifiable performance data
- **Never treat one lucky backtest as enough** - Single positive results are insufficient for validation
- **Never change thresholds silently** - All threshold changes must be explicit and logged
- **Never ignore fees** - Trading costs must always be included in calculations
- **Never ignore missing data** - Data availability must be confirmed before strategy evaluation
- **Never reject strategy quality before confirming data exists** - Data issues are system failures, not strategy rejections

### Parameter Management
- **Never optimize too many parameters blindly** - Limit the number of simultaneously optimized parameters
- **Always warn about overfitting risk** - Users must be informed when optimization may lead to overfitting
- **Respect parameter locks** - User-specified fixed parameters must remain fixed during optimization
- **Validate parameter ranges** - All parameters must stay within reasonable bounds
- **Document parameter changes** - All parameter modifications must be recorded in audit logs

### Validation Rigor
- **Require multiple validation dimensions** - Strategies must pass backtesting, OOS, WFA, and robustness checks
- **Statistical significance requirements** - Trade count must meet minimum thresholds for timeframe
- **Risk-adjusted performance** - Evaluate strategies using Sharpe, Calmar, and similar metrics
- **Cross-validation** - Test strategies across multiple pairs and timeframes when applicable
- **Stability testing** - Evaluate strategy behavior under parameter variations and market conditions

## AI Integrity

### AI Role Boundaries
- **AI is not the final judge** - Final strategy acceptance decisions come from backend validation and Freqtrade results
- **AI must not invent results** - All AI statements must be based on actual data and metrics
- **AI must not guarantee profits** - AI must never promise or guarantee trading profitability
- **AI must not freely modify strategy code without templates and validation** - Code generation must use deterministic templates
- **AI must ask for confirmation before write/run actions unless an explicit auto mode exists** - User approval is required for impactful actions
- **AI repair must have max iteration limits** - Repair attempts must be bounded (default: 3-5 iterations)

### AI Data Usage
- **AI must cite internal data when discussing results** - All AI claims must reference specific data sources
- **AI must not invent metrics** - Performance numbers must come from actual test results
- **AI must respect role permissions** - Each AI role must operate within defined boundaries
- **AI must use available run data only** - No fabrication or extrapolation beyond available information

### AI Safety
- **Audit all AI-assisted actions** - Every AI-influenced write/run operation must be logged
- **Provide rollback capabilities** - AI-suggested changes must be reversible
- **User approval workflows** - Critical AI suggestions require explicit user confirmation
- **Transparent AI reasoning** - AI must explain the rationale for suggestions

## UX Quality

### User Understanding
- **The user should always know what is happening** - System status must be clearly visible at all times
- **Every run stage must have status and explanation** - Each validation stage must show current state and purpose
- **Errors must be understandable** - Error messages must be actionable and clear
- **Logs must be expandable, not forced on the user** - Detailed logs should be available on demand, not forced
- **Results must explain why accepted or rejected** - Classification decisions must include detailed reasoning
- **Export paths must be visible** - Users must know exactly where files are exported

### User Control
- **Dangerous actions require confirmation** - Destructive or irreversible actions need explicit user approval
- **Clear action consequences** - Users must understand what will happen before confirming actions
- **Undo/redo where possible** - Provide ability to reverse actions when feasible
- **Progress indication** - Long-running operations must show progress
- **Cancellation support** - Users should be able to cancel long-running operations

### Interface Design
- **Consistent status colors** - Use established color conventions (green=good, red=bad, amber=warning)
- **Clear visual hierarchy** - Important information should be prominently displayed
- **Responsive design** - Interface must work across different screen sizes
- **Accessibility support** - Keyboard navigation, screen reader support, and color contrast compliance
- **Loading states** - Show loading indicators during data fetching and processing

## Testing Rules

### Backend Testing
- **Backend must include health checks** - All critical backend services must have health check endpoints
- **Backend must include unit tests for scoring and classification** - Trading metrics and classification logic must be tested
- **Backend must include tests for data availability logic** - Data checking and download logic must be tested
- **Backend must include tests for run lifecycle transitions** - State transitions and stage progression must be tested
- **Repository pattern testing** - Database operations must have test coverage
- **API contract testing** - API endpoints must be tested for correct request/response handling

### Frontend Testing
- **Frontend must include basic UI tests where practical** - Critical user flows should have automated tests
- **Component testing** - Individual components should be tested in isolation
- **Integration testing** - Key user workflows should be tested end-to-end
- **State management testing** - Application state logic must be tested

### Freqtrade Integration Testing
- **Freqtrade command runner must support test/fake mode** - Enable testing without actual Freqtrade installation
- **Mock Freqtrade responses** - Test UI and backend with simulated Freqtrade output
- **Result parser testing** - Freqtrade output parsing must be tested with various result formats
- **Config generation testing** - Generated Freqtrade configs must be validated

### System Integration
- **Full local smoke test must exist before final acceptance** - Complete system must be testable locally
- **End-to-end workflow testing** - Test complete user journeys from strategy upload to export
- **Error scenario testing** - Test system behavior under various failure conditions
- **Performance testing** - Verify system performance with realistic data volumes

### Test Data Management
- **Use test data fixtures** - Maintain consistent test data for reproducible tests
- **Isolate test environments** - Tests must not interfere with each other or production data
- **Clean up test artifacts** - Tests must clean up after themselves
- **Mock external dependencies** - Tests should not depend on external services when possible

## Documentation Quality

### Code Documentation
- **Public APIs must be documented** - All public functions and classes must have docstrings
- **Complex algorithms explained** - Non-obvious logic must be documented
- **Configuration options documented** - All settings and parameters must be explained
- **Error conditions documented** - Possible error states must be described

### User Documentation
- **Feature documentation** - All features must have user-facing documentation
- **Workflow guides** - Common user workflows should be documented
- **Troubleshooting guides** - Common issues and solutions should be documented
- **Configuration examples** - Example configurations should be provided

### System Documentation
- **Architecture documentation** - System design and architecture must be documented
- **API documentation** - All API endpoints must be documented
- **Data model documentation** - Database schemas and models must be documented
- **Integration documentation** - External system integrations must be documented

## Performance Standards

### Response Time
- **UI responsiveness** - Interface must respond to user interactions within 100ms
- **API response time** - Backend API calls should respond within 500ms for simple operations
- **Page load time** - Initial page load should complete within 2 seconds
- **Data loading** - Large datasets should load progressively with indicators

### Resource Usage
- **Memory efficiency** - Application should not consume excessive memory
- **Disk space management** - Artifacts and logs should have retention policies
- **CPU efficiency** - Long-running operations should not block the UI
- **Database optimization** - Database queries should be optimized and indexed

### Scalability
- **Local-first scaling** - System should handle reasonable local data volumes
- **Concurrent operations** - Support multiple simultaneous operations where applicable
- **Data growth handling** - System should gracefully handle growing data volumes

## Maintenance Standards

### Code Maintenance
- **Regular dependency updates** - Keep dependencies up to date with security patches
- **Deprecated feature removal** - Remove deprecated features after appropriate notice
- **Refactoring** - Regularly improve code structure and eliminate technical debt
- **Code review** - All changes should be reviewed before integration

### System Maintenance
- **Backup procedures** - Regular backups of critical data and configurations
- **Log rotation** - Implement log rotation to prevent disk space issues
- **Health monitoring** - System health should be regularly checked
- **Update procedures** - Clear procedures for updating system components

### User Support
- **Error reporting** - Provide clear error messages for user reporting
- **Debug information** - Include debug information for troubleshooting
- **Recovery procedures** - Document procedures for recovering from errors
- **Migration support** - Support data migration between versions

## Compliance and Ethics

### Trading Ethics
- **No profit guarantees** - Never guarantee trading profits or performance
- **Risk disclosure** - Always disclose trading risks and uncertainties
- **Realistic expectations** - Set realistic expectations about strategy performance
- **Transparency** - Be transparent about system limitations and assumptions

### Data Ethics
- **User data privacy** - Respect user data privacy and local-only principles
- **No data sharing** - Never share user data with external parties
- **Consent-based operations** - All operations should require user consent
- **Data ownership** - Users retain full ownership of their data

### Professional Standards
- **Honest communication** - Be honest about system capabilities and limitations
- **Responsible AI use** - Use AI responsibly with appropriate safeguards
- **Quality commitment** - Commit to high-quality engineering practices
- **Continuous improvement** - Regularly improve system quality and capabilities

## Enforcement

### Code Review
- All code changes must pass review against these quality rules
- Violations must be addressed before integration
- Exceptions require explicit justification and documentation

### Automated Checks
- Implement automated linters and formatters
- Use static analysis tools where applicable
- Include quality checks in CI/CD pipelines
- Run security scans on dependencies

### Regular Audits
- Regular audit of codebase for quality compliance
- Review of security practices and secret management
- Assessment of trading integrity and validation rigor
- Evaluation of AI usage and safety practices

## Summary

These quality rules establish the standards for building a reliable, secure, and maintainable AutoQuant system. Adherence to these rules ensures that the final product meets the owner's requirements for a serious local strategy validation application. Quality is not an afterthought but a fundamental requirement throughout the development process.
