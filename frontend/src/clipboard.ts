/**
 * Copies `text` to the clipboard. Resolves to false where the browser offers no clipboard, as on
 * a page that is not served over HTTPS, and where it refuses the copy.
 */
export async function copyText(text: string): Promise<boolean> {
  // The DOM types promise a clipboard, but an insecure page has none.
  const { clipboard } = navigator as { clipboard?: Clipboard };
  if (clipboard === undefined) return false;
  try {
    await clipboard.writeText(text);
    return true;
  } catch (error) {
    // The browser refuses with a DOMException when the page lacks the permission or the focus.
    if (error instanceof DOMException) return false;
    throw error;
  }
}
