import type { Settings } from './media';

// Keep edits made locally while adopting saved normalization and external updates.
export function rebaseSettingsDraft(before: Settings, draft: Settings, saved: Settings): Settings {
  const result = { ...saved };
  for (const key of Object.keys(draft) as (keyof Settings)[]) {
    if (JSON.stringify(draft[key]) !== JSON.stringify(before[key])) {
      (result as Record<string, unknown>)[key] = draft[key];
    }
  }
  return result;
}
