// utils/monacoLanguageFromFilename.ts
export function getMonacoLanguage(fileName: string): string | undefined {
  const ext = fileName.split('.').pop()?.toLowerCase();
  if (!ext) return undefined;
  const map: Record<string, string> = {
    // Web
    js: 'javascript', jsx: 'javascript', ts: 'typescript', tsx: 'typescript', html: 'html', htm: 'html', css: 'css', scss: 'scss', sass: 'sass', less: 'less', json: 'json', xml: 'xml',
    // Markdown
    md: 'markdown', markdown: 'markdown',
    // Python
    py: 'python', pyw: 'python',
    // C/C++
    c: 'c', h: 'cpp', cpp: 'cpp', cc: 'cpp', cxx: 'cpp', hpp: 'cpp', hxx: 'cpp',
    // C#
    cs: 'csharp',
    // Java
    java: 'java',
    // Kotlin
    kt: 'kotlin', kts: 'kotlin',
    // Go
    go: 'go',
    // Rust
    rs: 'rust',
    // Ruby
    rb: 'ruby', erb: 'erb',
    // PHP
    php: 'php',
    // Swift
    swift: 'swift',
    // Objective-C
    m: 'objective-c', mm: 'objective-c',
    // Dart
    dart: 'dart',
    // Scala
    scala: 'scala', sc: 'scala',
    // Shell
    sh: 'shell', bash: 'shell', zsh: 'shell',
    // PowerShell
    ps1: 'powershell', psm1: 'powershell',
    // Perl
    pl: 'perl', pm: 'perl',
    // R
    r: 'r',
    // Julia
    jl: 'julia',
    // Lua
    lua: 'lua',
    // SQL
    sql: 'sql',
    // Makefile
    makefile: 'makefile', mk: 'makefile',
    // Docker
    dockerfile: 'dockerfile',
    // Config
    ini: 'ini', conf: 'ini', toml: 'toml', env: 'dotenv',
    // Misc
    txt: 'plaintext', text: 'plaintext', log: 'log',
    // TypeScript declaration
    dts: 'typescript',
    // Assembly
    asm: 'asm', s: 'asm',
    // Visual Basic
    vb: 'vb',
    // F#
    fs: 'fsharp', fsx: 'fsharp',
    // Haskell
    hs: 'haskell', lhs: 'haskell',
    // Elm
    elm: 'elm',
    // OCaml
    ml: 'ocaml', mli: 'ocaml',
    // Groovy
    groovy: 'groovy', gvy: 'groovy', gy: 'groovy', gsh: 'groovy',
    // Batch
    bat: 'bat', cmd: 'bat',
    // Clojure
    clj: 'clojure', cljs: 'clojure', cljc: 'clojure', edn: 'clojure',
    // CoffeeScript
    coffee: 'coffeescript',
    // Crystal
    cr: 'crystal',
    // Visualforce
    vf: 'visualforce',
    // Apex
    apex: 'apex',
    // Solidity
    sol: 'solidity',
    // Terraform
    tf: 'terraform', tfvars: 'terraform',
    // Rego
    rego: 'rego',
    // Protobuf
    proto: 'protobuf',
    // GraphQL
    graphql: 'graphql', gql: 'graphql',
    // Svelte
    svelte: 'svelte',
    // Vue
    vue: 'vue',
  };

  return map[ext];
}
