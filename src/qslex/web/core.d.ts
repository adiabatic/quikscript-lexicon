export declare const TOKEN: RegExp;

export interface Token {
  word: string;
  start: number;
  end: number;
}

export interface SuggestContext {
  active: Set<string>;
  freq: Map<string, number>;
  groups: readonly string[];
  letters: string;
  rep: readonly string[][];
  limit?: number;
}

export declare function tokens(text: string): Token[];
export declare function accepts(active: Set<string>, word: string): boolean;
export declare function distance(a: string, b: string, cap: number): number;
export declare function suggest(word: string, ctx: SuggestContext): string[];
export declare function replaceOccurrence(
  source: string,
  word: string,
  occurrence: number,
  replacement: string,
): string;
export declare function replaceOccurrences(
  source: string,
  word: string,
  occurrences: number[],
  replacement: string,
): string;
export declare function stripFrontMatter(text: string): string;
