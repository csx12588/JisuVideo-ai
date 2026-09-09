import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..')
const page = fs.readFileSync(path.join(root, 'app/pages/index.vue'), 'utf8')
const api = fs.readFileSync(path.join(root, 'app/composables/useApi.ts'), 'utf8')

test('project creation exposes a ZIP production-package preview flow', () => {
  assert.match(page, /导入生产包/)
  assert.match(page, /accept="\.zip,application\/zip"/)
  assert.match(page, /productionPackageAPI\.preview\(file\)/)
  assert.match(page, /productionPackageAPI\.confirm\(/)
  assert.match(page, /productionPackagePreview\.project/)
  assert.match(page, /diagnostics\.missing/)
  assert.match(page, /diagnostics\.conflicts/)
  assert.match(page, /diagnostics\.warnings/)
  assert.match(page, /!productionPackagePreview\?\.can_confirm/)
})

test('production-package confirmation carries both fingerprints and an idempotency key', () => {
  assert.match(page, /preview_token: preview\.preview_token/)
  assert.match(page, /package_fingerprint: preview\.package\.package_fingerprint/)
  assert.match(page, /validation_fingerprint: preview\.package\.validation_fingerprint/)
  assert.match(page, /idempotency_key: productionPackageIdempotencyKey\.value/)
})

test('production-package API uploads multipart FormData and uses shared preview endpoints', () => {
  assert.match(api, /function productionPackagePreviewReq/)
  assert.match(api, /new FormData\(\)/)
  assert.match(api, /fd\.append\('file', file\)/)
  assert.match(api, /production-packages\/preview/)
  assert.match(api, /production-packages\/import\/confirm/)
})
