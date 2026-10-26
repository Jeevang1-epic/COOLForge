# Responsible use and operating limits

COOLForge is a prototype performance workbench. It is not certified for industrial
quality control, medical use, or safety-critical inspection. Synthetic mask scores
must not be represented as field accuracy.

Validate on representative production surfaces, camera settings, defect sizes, and
lighting conditions using independently labeled held-out data. A global pixel F1 floor
can hide misses on rare tiny defects. Review per-image rows, defect categories, precision,
recall, and examples of failures as well as the aggregate score. Downsampling and
morphological opening can erase thin cracks. Adaptive thresholding assumes dark local
defects and may miss bright defects or confuse texture with damage.

The core app sends no image to an external AI service. Uploads are decoded in server
memory, not persisted by the app. Streamlit holds session state while a session exists;
host logs, proxy configuration, and browser caching remain operator responsibilities.
Only synthetic data should be used on a public unauthenticated demo. The app has a
12 MB upload limit and rejects images above 16 million decoded pixels, but it is not
a hardened hostile-upload service. Use access restrictions and TLS for private use.

Optimization is bounded. A failed image invalidates a candidate. Human approval is
required for the final YAML export, and export does not deploy or modify any workload.
Review the proposed configuration on representative data before applying it elsewhere.

Benchmark results are environment-specific. CPU load, thermal state, interpreter,
OpenCV build, thread count, and sampling order affect latency. Comparisons refuse
mismatched artifacts; operator-edited JSON is not cryptographically attested. Do not
claim a speedup from one short run, or call a local OpenCV 4 result competition-compliant.

Keep credentials, keys, private images, and personal host information out of shared
artifacts. The raw environment verifier includes the module path; redact personal
directory names before publishing it and disclose redactions. Repository examples are
synthetic and licensed with the project. Stop AWS resources when no longer needed.
