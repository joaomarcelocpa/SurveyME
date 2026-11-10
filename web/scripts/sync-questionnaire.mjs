// Copia a fonte unica (../questionnaire.json) para dentro do app.
import { copyFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../../questionnaire.json");
const dst = resolve(here, "../src/data/questionnaire.json");
if (!existsSync(src)) {
  console.error("questionnaire.json nao encontrado na raiz do repositorio");
  process.exit(1);
}
mkdirSync(dirname(dst), { recursive: true });
copyFileSync(src, dst);
