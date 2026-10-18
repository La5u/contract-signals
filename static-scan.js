'use strict';

// Dependency-free scan logic: no DOM, fetch, filesystem, cache or implicit sort.
(function () {
  function integer(value, name, minimum = 0) {
    if (!Number.isSafeInteger(value) || value < minimum) {
      throw new TypeError(`${name} must be a safe integer >= ${minimum}`);
    }
    return value;
  }

  function aborted(signal) {
    if (signal && signal.aborted) {
      const error = new Error('Static scan aborted');
      error.name = 'AbortError';
      error.cause = signal.reason;
      throw error;
    }
  }

  // Race pending I/O/predicates against cancellation, even if a loader ignores
  // the signal. The underlying operation must use the signal to stop its work.
  async function wait(operation, signal) {
    aborted(signal);
    if (!signal) return operation();
    let listener;
    const cancellation = new Promise((resolve, reject) => {
      listener = () => {
        try { aborted(signal); } catch (error) { reject(error); }
      };
      signal.addEventListener('abort', listener, { once: true });
    });
    try {
      aborted(signal);
      return await Promise.race([
        Promise.resolve().then(() => { aborted(signal); return operation(); }),
        cancellation
      ]);
    } finally {
      signal.removeEventListener('abort', listener);
    }
  }

  // Manifest adapter: sequential loading, no prefetch/cache; loader returns a
  // row array or rejects. Never translate a failed/missing chunk into [].
  async function* loadChunks(descriptors, loadChunk, { signal } = {}) {
    if (typeof loadChunk !== 'function') throw new TypeError('loadChunk must be a function');
    let index = 0;
    for await (const descriptor of descriptors) {
      aborted(signal);
      const rows = await wait(() => loadChunk(descriptor, { signal, index }), signal);
      if (!Array.isArray(rows)) throw new TypeError(`Chunk ${index} must be an array`);
      yield rows;
      index++;
    }
  }

  /**
   * scan(chunks, options) -> Promise<{rows, offset, pageSize, scannedRows,
   *   matchedRows, scannedChunks, complete:true, exact:true}>
   * chunks: sync/async iterable of arrays, in desired output order.
   * predicate(row, {rowIndex, chunkIndex, indexInChunk, signal}): boolean/Promise<boolean>.
   * onProgress(snapshot): optional sync/async callback (no row references).
   * yieldControl(): optional async scheduler, called every yieldEvery rows.
   * Rejections carry .progress (complete:false, exact:false); no partial success.
   */
  async function scan(chunks, options = {}) {
    const {
      predicate = () => true, offset = 0, pageSize = 50, signal,
      onProgress, expectedChunks, expectedRows, yieldControl, yieldEvery = 1000
    } = options;
    integer(offset, 'offset');
    integer(pageSize, 'pageSize');
    integer(yieldEvery, 'yieldEvery', 1);
    if (!Number.isSafeInteger(offset + pageSize)) throw new TypeError('offset + pageSize must be safe');
    if (expectedChunks !== undefined) integer(expectedChunks, 'expectedChunks');
    if (expectedRows !== undefined) integer(expectedRows, 'expectedRows');
    for (const [name, fn] of [['predicate', predicate], ['onProgress', onProgress], ['yieldControl', yieldControl]]) {
      if (fn !== undefined && typeof fn !== 'function') throw new TypeError(`${name} must be a function`);
    }
    let scannedRows = 0, matchedRows = 0, scannedChunks = 0;
    const rows = [];
    const snapshot = (complete = false) => ({
      offset, pageSize, scannedRows, matchedRows, scannedChunks, complete, exact: complete
    });
    const report = async (complete = false) => {
      if (onProgress) await wait(() => onProgress(snapshot(complete)), signal);
      aborted(signal);
    };
    let iterator;
    let ended = false;
    try {
      aborted(signal);
      const factory = chunks && (chunks[Symbol.asyncIterator] || chunks[Symbol.iterator]);
      if (typeof factory !== 'function') throw new TypeError('chunks must be an iterable of row arrays');
      iterator = factory.call(chunks);
      await report();
      while (true) {
        const next = await wait(() => iterator.next(), signal);
        if (!next || typeof next !== 'object') throw new TypeError('Invalid iterator result');
        if (next.done) { ended = true; break; }
        const chunk = next.value;
        if (!Array.isArray(chunk)) throw new TypeError(`Chunk ${scannedChunks} must be an array`);
        if (expectedChunks !== undefined && scannedChunks >= expectedChunks) throw new Error('More chunks than expected');
        for (let indexInChunk = 0; indexInChunk < chunk.length; indexInChunk++) {
          aborted(signal);
          if (expectedRows !== undefined && scannedRows >= expectedRows) throw new Error('More rows than expected');
          const row = chunk[indexInChunk];
          const matches = await wait(() => predicate(row, {
            rowIndex: scannedRows, chunkIndex: scannedChunks, indexInChunk, signal
          }), signal);
          aborted(signal);
          if (typeof matches !== 'boolean') throw new TypeError('predicate must return a boolean');
          if (matches) {
            if (matchedRows >= offset && rows.length < pageSize) rows.push(row);
            matchedRows++;
          }
          scannedRows++;
          if (scannedRows % yieldEvery === 0) {
            await report();
            if (yieldControl) await wait(() => yieldControl(), signal);
          }
        }
        scannedChunks++;
        await report();
      }
      if (expectedChunks !== undefined && scannedChunks !== expectedChunks) throw new Error('Fewer chunks than expected');
      if (expectedRows !== undefined && scannedRows !== expectedRows) throw new Error('Fewer rows than expected');
      await report(true);
      return { ...snapshot(true), rows };
    } catch (cause) {
      // Wrap rather than mutate a frozen/user-owned exception. All failures,
      // including cancellation, expose only explicitly partial counts.
      const error = new Error(cause && cause.message || String(cause));
      error.name = cause && cause.name === 'AbortError' ? 'AbortError' : 'StaticScanError';
      error.cause = cause;
      error.progress = snapshot();
      throw error;
    } finally {
      if (iterator && !ended && typeof iterator.return === 'function') {
        // Do not hang cancellation waiting for an uncooperative async iterator.
        try { Promise.resolve(iterator.return()).catch(() => {}); } catch (_) { /* preserve scan error */ }
      }
    }
  }

  const api = { scan, loadChunks };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else globalThis.StaticScan = api;
})();
