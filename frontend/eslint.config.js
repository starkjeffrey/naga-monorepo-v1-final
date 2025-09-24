import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import * as parserVue from 'vue-eslint-parser'
import configTypescript from '@vue/eslint-config-typescript'
import configPrettier from '@vue/eslint-config-prettier'

export default [
  {
    name: 'app/files-to-lint',
    files: ['**/*.{ts,mts,tsx,vue,js,jsx}'],
  },

  {
    name: 'app/files-to-ignore',
    ignores: [
      '**/dist/**',
      '**/dist-ssr/**',
      '**/coverage/**',
      '**/node_modules/**',
      '**/dev-dist/**',
      '**/public/**',
      '**/debug/**',
      '**/test-pwa.js',
      '**/capacitor.config.js',
      '**/vite.config.js',
      '**/vitest.config.js',
      '**/eslint.config.js'
    ],
  },

  // Base JavaScript rules
  js.configs.recommended,

  // Vue.js rules
  ...pluginVue.configs['flat/recommended'],

  // TypeScript rules
  ...configTypescript(),

  // Prettier rules (must be last)
  configPrettier,

  // Custom rules for Vue 3 + Quasar
  {
    name: 'app/vue-rules',
    languageOptions: {
      parser: parserVue,
      parserOptions: {
        parser: '@typescript-eslint/parser',
        ecmaVersion: 'latest',
        sourceType: 'module',
      },
      globals: {
        console: 'readonly',
        window: 'readonly',
        document: 'readonly',
        navigator: 'readonly',
        localStorage: 'readonly',
        sessionStorage: 'readonly',
        fetch: 'readonly',
        process: 'readonly',
        __dirname: 'readonly',
        global: 'readonly',
        FormData: 'readonly',
        FileReader: 'readonly',
        atob: 'readonly',
        btoa: 'readonly',
        Blob: 'readonly',
        File: 'readonly',
        CustomEvent: 'readonly',
        URL: 'readonly',
        URLSearchParams: 'readonly',
      },
    },
    rules: {
      // Vue 3 Composition API preferences
      'vue/component-api-style': ['warn', ['script-setup', 'composition']],
      'vue/component-name-in-template-casing': ['warn', 'kebab-case'],
      'vue/custom-event-name-casing': ['warn', 'camelCase'],
      'vue/define-macros-order': [
        'warn',
        {
          order: ['defineProps', 'defineEmits', 'defineExpose', 'defineSlots', 'defineModel'],
        },
      ],
      'vue/no-undef-components': 'off', // Quasar components not recognized
      'vue/no-unused-refs': 'warn',
      'vue/no-useless-v-bind': 'warn',
      'vue/prefer-import-from-vue': 'warn',
      'vue/prefer-separate-static-class': 'warn',
      'vue/require-macro-variable-name': 'warn',

      // Quasar framework compatibility
      'vue/no-reserved-component-names': 'off', // Quasar uses reserved names
      'vue/multi-word-component-names': 'off', // Allow single word components for pages

      // PWA and mobile-first considerations
      'vue/max-attributes-per-line': [
        'warn',
        {
          singleline: 5,
          multiline: 1,
        },
      ],
      'vue/first-attribute-linebreak': [
        'warn',
        {
          singleline: 'ignore',
          multiline: 'below',
        },
      ],

      // Accessibility rules
      'vue/no-template-target-blank': 'warn',
      'vue/no-static-inline-styles': 'warn',

      // Performance considerations
      'vue/no-v-html': 'warn',
      'vue/require-v-for-key': 'error',
      'vue/no-mutating-props': 'error',
      'vue/block-lang': 'off',

      // TypeScript integration
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'warn',

      // General code quality
      'no-console': 'warn',
      'no-debugger': 'warn',
      'no-unused-vars': 'off', // Handled by TypeScript
      'prefer-const': 'warn',
      'no-var': 'error',
      'object-shorthand': 'warn',
      'prefer-template': 'warn',
    },
  },

  // Test file specific configuration
  {
    name: 'app/test-files',
    files: ['**/test/**/*.js', '**/src/test/**/*.js', '**/*.test.js', '**/*.spec.js'],
    languageOptions: {
      globals: {
        vi: 'readonly',
        describe: 'readonly',
        it: 'readonly',
        test: 'readonly',
        expect: 'readonly',
        beforeEach: 'readonly',
        afterEach: 'readonly',
        beforeAll: 'readonly',
        afterAll: 'readonly',
        global: 'readonly',
        window: 'readonly',
      },
    },
  },
]
