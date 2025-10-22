// ABOUTME: Utility functions for generating conversation titles from messages
// ABOUTME: Handles word extraction, character limits, and edge cases

/**
 * Generate a conversation title from a message.
 * Extracts first 3-4 words, max 50 characters.
 *
 * @param content - Message content to generate title from
 * @param maxLength - Maximum title length (default: 50)
 * @returns Generated title
 */
export function generateTitleFromMessage(content: string, maxLength: number = 50): string {
  // Trim and clean the content
  const cleaned = content.trim();

  // Handle empty message
  if (!cleaned) {
    return "New Chat";
  }

  // Split into words
  const words = cleaned.split(/\s+/);

  // Take first 3-4 words
  const wordCount = Math.min(words.length, 4);
  const firstWords = words.slice(0, wordCount).join(' ');

  // If within limit, return as-is
  if (firstWords.length <= maxLength) {
    return firstWords;
  }

  // Try with 3 words
  if (wordCount === 4) {
    const threeWords = words.slice(0, 3).join(' ');
    if (threeWords.length <= maxLength) {
      return threeWords;
    }
  }

  // Truncate at character boundary with ellipsis
  return firstWords.substring(0, maxLength - 3) + '...';
}
