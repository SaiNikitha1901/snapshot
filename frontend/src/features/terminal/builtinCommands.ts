/** Command names the terminal recognizes at all, for tab-completion and
 * `help`. Doesn't include arguments -- just first-token candidates. */
export const KNOWN_COMMAND_NAMES = [
  'init',
  'add',
  'commit',
  'branch',
  'checkout',
  'merge',
  'log',
  'echo',
  'cat',
  'ls',
  'mkdir',
  'rm',
  'touch',
  'edit',
  'clear',
  'history',
  'help',
]

export const HELP_LINES = [
  'Snapshot -- educational Git internals explorer. Watch Git think.',
  '',
  'Git commands:',
  '  init                 create a new repository',
  '  add <path>|.         stage a file, or all project files',
  '  commit -m <message>  commit staged changes',
  '  branch [name]        list branches, or create one at HEAD',
  '  checkout <target>    switch to a branch, or detach onto a commit',
  '  merge <branch>       merge a branch into the current branch',
  '  log                  show commit history from HEAD',
  '',
  'Files:',
  '  echo <text> [> file]   print text, or write it to a file',
  '  cat <file>             print a file\'s contents',
  '  ls [dir]               list a directory',
  '  mkdir <dir>            create a directory',
  '  rm <file>              remove a file',
  '  touch <file>           create an empty file',
  '  edit <file>            open a file in the inline editor',
  '',
  'Terminal:',
  '  clear     clear the screen',
  '  history   show previously run commands',
  '  help      show this message',
]

/** These never reach the backend -- they carry no repository state,
 * so there's nothing for a StudioResponse to report. */
export const LOCAL_ONLY_COMMANDS = new Set(['clear', 'history', 'help'])
