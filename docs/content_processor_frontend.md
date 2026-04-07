# Content Processor Frontend Skeleton

## Scope

- This page is the formal Content Processor entry.
- It is intentionally separated from the legacy multi-style demo flow.
- Current formal Generate uses the backend Content Processor API.
- The mock provider file is retained only as a reference and fallback sample source, not as the formal main flow.
- Optional reference media inputs are now part of the formal Content Processor input layer.

## New Entry

- Route: `/content-processor`
- Legacy demo remains at `/`
- Formal Generate API: `/content-processor/generate`
- The formal Generate request now uses `multipart/form-data`.

## Directory Layout

- `frontend/routes/content_processor.py`: formal page route registration
- `modules/content_processor/content_package_builder.py`: formal content package generation layer
- `modules/content_processor/reference_media_store.py`: reference image/video upload persistence and group normalization
- `templates/content_processor/dashboard.html`: formal dashboard template
- `static/css/content_processor/dashboard.css`: dashboard styles
- `static/js/content_processor/dashboard.js`: dashboard interaction
- `static/js/content_processor/mock_content_package.js`: mock content package provider

## Next API Hook Point

- Frontend request entry: `static/js/content_processor/dashboard.js`
- Current functions: `handleGenerate(event)` and `regenerateCurrentContentPackage()`
- Shared request function: `requestContentPackage(requestReason)`
- Current API path: `fetch('/content-processor/generate', ...)`
- Backend route entry: `frontend/routes/content_processor.py`
- Content package builder: `modules/content_processor/content_package_builder.py`
- Feedback mapper: `modules/content_processor/feedback_mapper.py`
- Feedback adapter: `modules/content_processor/feedback_adapter.py`

## Feedback Regenerate

- Regenerate still uses the same single button.
- If `feedback_text` is empty, the page runs ordinary regenerate.
- If `feedback_text` is non-empty, the page treats the same button click as feedback-driven regenerate.
- Backend still reuses `/content-processor/generate` and interprets `feedback_text` inside the builder layer.
- Feedback chain is now explicit: `feedback_text -> feedback_mapper -> structured constraints -> prompt block -> builder`.
- Light feedback mapping currently covers:
	- shorter title
	- less academic tone / more spoken tone
	- more storylike / more engaging opening
	- tighter / looser expression
	- richer keywords
	- lighter / clearer / denser highlights
- If feedback is not matched by rules, the raw feedback text is still inserted into the prompt as natural-language constraints.

## Reference Media Inputs

- Frontend fields:
	- `reference_images[]`
	- `reference_images_note`
	- `reference_images_role_hint`
	- `reference_videos[]`
	- `reference_videos_note`
	- `reference_videos_role_hint`
- Upload storage:
	- images: `data/users/default_user/uploads/images/`
	- videos: `data/users/default_user/uploads/videos/`
- Builder context includes `[Reference Media Inputs]` with count, role, and note.
- Returned `content package` now includes `input_sources.priority_policy = user_uploaded_media_first`.

## Placeholder Areas

- Confirm is now a frontend-only confirmed state update for the current package.
- Regenerate now reuses the formal `/content-processor/generate` API with the current form values and current file inputs.
- Feedback history is not implemented.
- Multi-round preference memory is not implemented.
- Manual edit form is still a placeholder for Task-CP4.