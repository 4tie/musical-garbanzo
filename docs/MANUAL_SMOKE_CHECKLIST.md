# Manual Smoke Checklist for Safe Run Controls

This checklist is for manual smoke testing of the safe run controls implementation. Do not run real pipelines unless explicitly authorized.

## Baseline Start Page

### Page Load
- [ ] Open `/baseline` route
- [ ] Verify page title is "Start Baseline Evaluation"
- [ ] Verify description is "Run a local validation workflow to evaluate your strategy's performance. This does not place trades."
- [ ] Verify form loads without errors
- [ ] Verify all form fields are visible and properly labeled

### Form Validation
- [ ] Click "Start Baseline Evaluation" with empty form
- [ ] Verify validation errors appear at top of form
- [ ] Verify "strategy_name" field shows error
- [ ] Verify "pairs" field shows error
- [ ] Verify "timeframe" field shows error
- [ ] Verify "risk_profile" field shows error
- [ ] Verify "user_confirmed" field does NOT show error (pre-confirm validation)
- [ ] Verify confirmation dialog does NOT open with invalid form

### Form Interaction
- [ ] Fill strategy name with valid value
- [ ] Verify strategy name error clears
- [ ] Fill pairs with valid value (e.g., "BTC/USDT")
- [ ] Verify pairs error clears
- [ ] Fill pairs with invalid format (e.g., "BTCUSDT")
- [ ] Verify pairs validation error appears (invalid format)
- [ ] Fill pairs with valid format again
- [ ] Verify pairs error clears
- [ ] Fill timeframe with valid value (e.g., "1h")
- [ ] Verify timeframe error clears
- [ ] Fill risk profile with valid value (e.g., "balanced")
- [ ] Verify risk profile error clears
- [ ] Verify validation errors are all cleared

### Confirmation Dialog
- [ ] Click "Start Baseline Evaluation" with valid form
- [ ] Verify confirmation dialog opens
- [ ] Verify dialog title is "Confirm Baseline Evaluation"
- [ ] Verify action summary shows correct values
- [ ] Verify resource warning is displayed
- [ ] Verify safety notes are displayed
- [ ] Verify confirmation checkbox is visible
- [ ] Verify "Confirm and Start" button is disabled
- [ ] Check confirmation checkbox
- [ ] Verify "Confirm and Start" button is enabled

### Cancel Confirmation
- [ ] Click "Cancel" button
- [ ] Verify dialog closes
- [ ] Verify form values are preserved
- [ ] Verify no API request was made

### Escape Key
- [ ] Open confirmation dialog again
- [ ] Press Escape key
- [ ] Verify dialog closes
- [ ] Verify form values are preserved

### POST Request
- [ ] Open confirmation dialog
- [ ] Check confirmation checkbox
- [ ] Click "Confirm and Start" button
- [ ] Verify button shows "Starting..." and is disabled
- [ ] Verify POST request is sent to `/api/baseline/start`
- [ ] Verify request payload includes all form fields
- [ ] Verify request includes `user_confirmed: true`

### Progress Panel
- [ ] After successful POST, verify progress panel appears
- [ ] Verify status is displayed
- [ ] Verify run ID is displayed
- [ ] Verify type is displayed as "Baseline Evaluation"
- [ ] Verify polling indicator is shown (animated ping)
- [ ] Verify "Refresh" button is visible
- [ ] Verify "View Details" button is not shown (not terminal state)

### Result Display
- [ ] Wait for terminal state (completed or failed)
- [ ] Verify result banner appears
- [ ] Verify "View Details" button appears
- [ ] Verify polling indicator stops
- [ ] Verify "Refresh" button is enabled

### Action Audit Section
- [ ] Scroll to "Action Audit" section
- [ ] Verify "What this action will do" list is displayed
- [ ] Verify "This will NOT" list is displayed
- [ ] Verify "To inspect result" section is displayed

### Safety Information Section
- [ ] Scroll to "Safety Information" section
- [ ] Verify safety notes are displayed
- [ ] Verify "This runs a local validation workflow" is shown
- [ ] Verify "This does not place trades" is shown

## Optimization Start Page

### Page Load
- [ ] Open `/optimization` route
- [ ] Verify page title is "Start Safe Optimization"
- [ ] Verify description is "Run Hyperopt to optimize strategy parameters. This is resource-intensive and may take significant time."
- [ ] Verify form loads without errors
- [ ] Verify all form fields are visible and properly labeled

### Resource Warning Section
- [ ] Verify "Resource Warning" section is displayed at top
- [ ] Verify "Hyperopt can take time" is shown
- [ ] Verify "More epochs means longer runtime" is shown
- [ ] Verify "This may create runtime artifacts" is shown
- [ ] Verify "Best Hyperopt trial is not automatically approved" is shown

### Form Validation
- [ ] Click "Start Optimization" with empty form
- [ ] Verify validation errors appear at top of form
- [ ] Verify "strategy_name" field shows error
- [ ] Verify "pairs" field shows error
- [ ] Verify "timeframe" field shows error
- [ ] Verify "risk_profile" field shows error
- [ ] Verify "epochs" field shows error
- [ ] Verify "spaces" field shows error
- [ ] Verify "user_confirmed" field does NOT show error (pre-confirm validation)
- [ ] Verify confirmation dialog does NOT open with invalid form

### Invalid Epochs
- [ ] Set epochs to 0
- [ ] Click "Start Optimization"
- [ ] Verify epochs validation error appears
- [ ] Set epochs to 201
- [ ] Click "Start Optimization"
- [ ] Verify epochs validation error appears (max 200)
- [ ] Set epochs to 20 (valid)
- [ ] Verify epochs error clears

### Unsupported Spaces
- [ ] Verify only "buy" and "sell" spaces are available
- [ ] Verify "roi", "stoploss", "trailing", "protection" are not selectable
- [ ] Select "buy" and "sell" spaces
- [ ] Verify spaces are valid
- [ ] Verify request builder filters to buy/sell only

### Confirmation Dialog
- [ ] Click "Start Optimization" with valid form
- [ ] Verify confirmation dialog opens
- [ ] Verify dialog title is "Confirm Optimization"
- [ ] Verify action summary shows correct values
- [ ] Verify Hyperopt indicator is shown
- [ ] Verify resource warning is displayed
- [ ] Verify safety notes are displayed
- [ ] Verify confirmation checkbox is visible
- [ ] Verify "Confirm and Start" button is disabled
- [ ] Check confirmation checkbox
- [ ] Verify "Confirm and Start" button is enabled

### POST Request
- [ ] Click "Confirm and Start" button
- [ ] Verify button shows "Starting..." and is disabled
- [ ] Verify POST request is sent to `/api/optimization/start`
- [ ] Verify request payload includes all form fields
- [ ] Verify request includes `user_confirmed: true`
- [ ] Verify request includes `epochs: 20` (default)
- [ ] Verify request includes `spaces: ['buy', 'sell']` (default)

### Progress Panel
- [ ] After successful POST, verify progress panel appears
- [ ] Verify status is displayed
- [ ] Verify run ID is displayed
- [ ] Verify type is displayed as "Optimization"
- [ ] Verify polling indicator is shown (animated ping)
- [ ] Verify "Refresh" button is visible
- [ ] Verify "View Details" button is not shown (not terminal state)

### Route Link
- [ ] Wait for terminal state (completed or failed)
- [ ] Verify result banner appears
- [ ] Verify "View Details" button appears
- [ ] Click "View Details" button
- [ ] Verify navigation to `/optimization/{runId}`

### Action Audit Section
- [ ] Scroll to "Action Audit" section
- [ ] Verify "What this action will do" list is displayed
- [ ] Verify "This will NOT" list is displayed
- [ ] Verify "To inspect result" section is displayed

### Safety Information Section
- [ ] Scroll to "Safety Information" section
- [ ] Verify safety notes are displayed
- [ ] Verify "This runs a local Hyperopt workflow" is shown
- [ ] Verify "This does not place trades" is shown
- [ ] Verify "Best trial is not automatically approved" is shown

## Accessibility

### Keyboard Navigation
- [ ] Tab through form fields
- [ ] Verify focus is visible on all interactive elements
- [ ] Verify Tab order is logical
- [ ] Verify Enter key submits form when focus is on submit button
- [ ] Verify Escape key closes confirmation dialog

### Screen Reader
- [ ] Verify all form fields have associated labels
- [ ] Verify all buttons have accessible labels
- [ ] Verify dialog has `role="dialog"` and `aria-modal="true"`
- [ ] Verify dialog title has `aria-labelledby`
- [ ] Verify status indicators are not color-only

### Focus Management
- [ ] Verify focus is trapped in confirmation dialog (if feasible)
- [ ] Verify focus returns to trigger element after dialog closes
- [ ] Verify focus is visible on all elements

## Reduced Motion

### Polling Indicator
- [ ] Enable reduced motion in OS settings
- [ ] Start a run and verify polling indicator respects reduced motion
- [ ] Verify polling interval is doubled (4 seconds instead of 2)

### Transitions
- [ ] Verify no unnecessary animations
- [ ] Verify transitions respect reduced motion preference

## Error Handling

### Network Errors
- [ ] Verify network errors are displayed gracefully
- [ ] Verify error message is clear
- [ ] Verify retry option is available

### Controlled Failures
- [ ] Verify controlled failure banner is displayed
- [ ] Verify retry copy is shown
- [ ] Verify controlled failure is distinguished from system failure

### Debug Copy
- [ ] Click "Copy Debug Info" button
- [ ] Verify debug info is copied to clipboard
- [ ] Verify debug info does not include secrets
- [ ] Verify "Copied!" feedback is shown

## Safety Verification

### No Live Trading Controls
- [ ] Verify no live trading controls exist
- [ ] Verify trading_mode is hardcoded to "spot"
- [ ] Verify no exchange order controls exist

### No Approval/Export Controls
- [ ] Verify no approval controls exist
- [ ] verify apply_decision_to_run is set to false
- [ ] Verify no export controls exist

### No External Service Integration
- [ ] Verify no Discord integration controls exist
- [ ] Verify no Ollama integration controls exist
- [ ] Verify no AI repair controls exist

## Notes

- This checklist is for manual smoke testing only
- Do not run real pipelines unless explicitly authorized
- Final validation is frontend build/lint/manual UI behavior only
- All backend execution requires explicit authorization
