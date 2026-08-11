/**
 * FOST — Gmail → Receipts Log (Google Apps Script)
 * Auto-appends parts/receipt emails to the "FOST — Receipts Log" sheet.
 *
 * WHY THIS INSTEAD OF IFTTT: IFTTT's Gmail service exposes no "new email"
 * trigger (retired), so it can't watch your inbox. This script is the native,
 * free, reliable path. Runs on a time trigger; labels processed threads so it
 * never double-logs.
 *
 * SETUP (≈2 min):
 *  1. Open the "FOST — Receipts Log" sheet in Drive → Extensions → Apps Script.
 *  2. Paste this whole file, replacing anything there. Save.
 *  3. Run `install()` once (authorize when prompted). Done — it now runs hourly.
 *  4. To backfill older receipts once, run `runOnce()` after widening LOOKBACK.
 *
 * TUNE: edit VENDOR_HINTS / SEARCH below to taste. Amounts are best-effort
 * (regex on the body); always eyeball the "Total $" column — flagged rows say
 * "auto - verify".
 */

const SHEET_ID = '1Y5lDZIvOPDb0Lnn6e575NiTVaS0s_MPTd4s1nyWj_Bw'; // FOST — Receipts Log
const PROCESSED_LABEL = 'FOST-Logged';
const LOOKBACK = 'newer_than:2d';

// Only treat as a receipt if it looks like a purchase AND (optionally) touches a car vendor/keyword.
const SEARCH = LOOKBACK +
  ' (subject:(order OR receipt OR invoice OR "order confirmation" OR purchase OR shipped)) ' +
  ' -from:no-reply@google.com -label:' + PROCESSED_LABEL;

// If a message matches none of these, it's still logged but tagged "review".
const VENDOR_HINTS = ['mishimoto','cobb','rockauto','forscan','obdlink','ebay','amazon',
  'summit','fcp','steeda','mountune','whiteline','turbosmart','autozone','oreilly',
  'idatalink','crutchfield','tasca','levittown','focus','st','radiator','intercooler',
  'downpipe','coilover','brembo','recaro','maestro'];

function install() {
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('runOnce').timeBased().everyHours(1).create();
  runOnce();
}

function runOnce() {
  const label = GmailApp.getUserLabelByName(PROCESSED_LABEL) || GmailApp.createLabel(PROCESSED_LABEL);
  const sheet = SpreadsheetApp.openById(SHEET_ID).getSheets()[0];
  const threads = GmailApp.search(SEARCH, 0, 40);
  threads.forEach(thread => {
    const msg = thread.getMessages()[thread.getMessageCount() - 1];
    const row = parseReceipt(msg);
    if (row) sheet.appendRow(row);
    thread.addLabel(label); // mark handled either way
  });
}

function parseReceipt(msg) {
  const from = msg.getFrom();
  const subject = msg.getSubject() || '';
  const date = Utilities.formatDate(msg.getDate(), Session.getScriptTimeZone(), 'yyyy-MM-dd');
  const body = (msg.getPlainBody() || '').slice(0, 4000);
  const hay = (from + ' ' + subject + ' ' + body).toLowerCase();

  const vendor = (from.match(/"?([^"<]+)"?\s*</) || [null, from])[1].trim();
  const amountMatch = body.match(/(?:grand total|order total|total)[^$]{0,20}\$\s?([0-9][0-9,]*\.[0-9]{2})/i)
    || body.match(/\$\s?([0-9][0-9,]*\.[0-9]{2})/);
  const amount = amountMatch ? amountMatch[1].replace(/,/g, '') : 'TBD';
  const isCar = VENDOR_HINTS.some(k => hay.indexOf(k) !== -1);
  const link = 'https://mail.google.com/mail/u/0/#inbox/' + msg.getId();

  // Columns must match the sheet header:
  // Date | Vendor | Item | Project | Bundle | Qty | Unit $ | Total $ | Order # | Source | Ref/Link | Notes
  return [date, vendor, subject, '', '', '', '', amount, '', 'Gmail-auto', link,
          (isCar ? 'auto - verify amount/project' : 'auto - REVIEW: may not be a car part')];
}
