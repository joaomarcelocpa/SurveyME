import raw from "@/data/questionnaire.json";

export type Option = { value: string | number; label: string };
export type Item = {
  id: string;
  text: string;
  type: "single" | "multi" | "likert" | "open";
  role: "screening" | "profile" | "measure" | "attention" | "open";
  required: boolean;
  options?: Option[];
  pass_value?: string;
  expected?: number;
  max_length?: number;
};
export type Questionnaire = {
  version: string;
  title: string;
  order: string[];
  items: Item[];
};

export const questionnaire = raw as unknown as Questionnaire;

export const itemsInOrder: Item[] = questionnaire.order.map((id) => {
  const it = questionnaire.items.find((i) => i.id === id);
  if (!it) throw new Error(`Item ${id} ausente em questionnaire.json`);
  return it;
});
