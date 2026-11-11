/**
 * Receptor da copia secundaria das respostas (Google Apps Script).
 * O site envia, depois de gravar no banco, uma linha por resposta; aqui ela vira uma linha da planilha,
 * no formato de uma planilha do Google Forms. O banco (Neon) continua sendo a fonte oficial.
 *
 * Propriedade do script (Configuracoes do projeto > Propriedades do script): SECRET = mesmo valor de
 * SHEETS_WEBHOOK_SECRET na Vercel. Sem ela, nada e gravado.
 */
const SHEET_NAME = "Respostas";

function doPost(e) {
  const secret = PropertiesService.getScriptProperties().getProperty("SECRET");
  let body;
  try {
    body = JSON.parse(e.postData.contents);
  } catch (_) {
    return reply({ ok: false, error: "json" });
  }
  if (!secret || body.token !== secret) return reply({ ok: false, error: "nao autorizado" });
  if (!Array.isArray(body.headers) || !Array.isArray(body.row) ||
      body.headers.length !== body.row.length || body.row.length < 2 || body.row.length > 60) {
    return reply({ ok: false, error: "formato" });
  }

  const lock = LockService.getScriptLock();
  lock.waitLock(30000); // envios simultaneos entram um de cada vez
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sh = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);

    if (sh.getLastRow() === 0) {
      sh.appendRow(body.headers);
      sh.setFrozenRows(1);
      sh.getRange(1, 1, 1, body.headers.length).setFontWeight("bold").setWrap(true);
    }

    // A ultima coluna e o ID da resposta: evita linha repetida se o site reenviar.
    const idCol = body.row.length;
    const id = String(body.row[idCol - 1]);
    const last = sh.getLastRow();
    if (last > 1 && sh.getRange(2, idCol, last - 1, 1).createTextFinder(id).matchEntireCell(true).findNext()) {
      return reply({ ok: true, duplicate: true });
    }

    const row = body.row.slice();
    row[0] = Utilities.formatDate(new Date(row[0]), "America/Sao_Paulo", "dd/MM/yyyy HH:mm:ss");
    sh.appendRow(row);
    return reply({ ok: true });
  } finally {
    lock.releaseLock();
  }
}

function reply(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
