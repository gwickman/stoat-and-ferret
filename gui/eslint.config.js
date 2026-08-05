import js from '@eslint/js'
import globals from 'globals'
import reactPlugin from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import a11y from 'eslint-plugin-jsx-a11y'
import unicorn from 'eslint-plugin-unicorn'
import sonarjs from 'eslint-plugin-sonarjs'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
      a11y.flatConfigs.recommended,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
      parserOptions: {
        project: ['./tsconfig.app.json', './tsconfig.node.json', './tsconfig.eslint.json'],
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: {
      react: reactPlugin,
    },
    rules: {
      // Allow role on interactive div/span elements when aria-label is present.
      // The codebase uses role="button" on divs for custom interactive controls.
      'jsx-a11y/no-static-element-interactions': [
        'warn',
        {
          handlers: [
            'onClick',
            'onMouseDown',
            'onMouseUp',
            'onKeyPress',
            'onKeyDown',
            'onKeyUp',
          ],
        },
      ],
      'react/no-array-index-key': 'error',
      'react/no-unused-prop-types': 'error',
      '@typescript-eslint/prefer-readonly': 'error',
    },
  },
  {
    files: ['**/*.{ts,tsx}'],
    plugins: { unicorn },
    rules: {
      'unicorn/prefer-number-properties': 'error',
      'unicorn/prefer-export-from': 'error',
      'unicorn/no-typeof-undefined': 'error',
      'unicorn/prefer-string-replace-all': 'error',
      'unicorn/no-useless-fallback-in-spread': 'error',
      'unicorn/prefer-set-has': 'error',
      'unicorn/prefer-string-raw': 'error',
    },
  },
  {
    files: ['**/*.{ts,tsx}'],
    plugins: { sonarjs },
    rules: {
      'sonarjs/no-collection-size-mischeck': 'error',
      'sonarjs/no-identical-functions': 'error',
      'sonarjs/no-incomplete-assertions': 'error',
      'sonarjs/no-ignored-exceptions': 'error',
      'sonarjs/sonar-prefer-read-only-props': 'error',
      'sonarjs/sonar-prefer-optional-chain': 'error',
    },
  },
  {
    // Scoped to vitest.setup.ts only: the ResizeObserver stub methods are
    // deliberate empty no-ops for jsdom compatibility; the suppressions below
    // must be written against an active rule (BL-718-AC-5).
    files: ['vitest.setup.ts'],
    rules: {
      '@typescript-eslint/no-empty-function': 'error',
    },
  },
])
