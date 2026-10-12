# Pictures and Documents

SuperLocalMemory can save screenshots, photos and PDFs and find them later by describing them. A picture model runs on your computer, OCR reads the text inside pictures, and each PDF page is indexed by its picture and its text. No generative model looks at your files. The feature is off until you turn it on, and turning it on does not change your existing memories or their embeddings: pictures and PDF pages are stored next to them, in their own database.

## What your computer needs

| | |
|---|---|
| Memory (RAM) | 16 GB. Computers sold as 16 GB report a little less, so the check passes from 15 GiB. |
| Disk | About 1.5 GB for the models, plus what you save (up to 2 GB of pictures and PDFs per profile). |
| Systems | macOS on Apple Silicon, Windows x64, Linux x86_64 and Linux ARM64 with a glibc (Debian, Ubuntu, Fedora). Python 3.12 to 3.14. |
| Not supported | Windows on ARM and Intel Macs. Text memory works there as before. |

Below 16 GB the switch is refused with the reason, because the picture model and a large PDF together can push a smaller machine into swapping. If you accept that risk, set `SLM_MEDIA_ALLOW_LOW_RAM=1` in the environment SLM starts from and turn the feature on again.

## Turn it on

From a terminal:

```bash
slm features                  # what is on, and what you can turn on
slm media enable              # shows the download size and asks first
slm media status              # how set-up is going
```

Or use the dashboard: **Settings**, then **Images & documents**, or the **Documents & Images** workspace. The npm installer and upgrader also offer it. `slm media enable` starts SuperLocalMemory if it is not running. The first time, it downloads about 1.5 GB.

## Save and find

Use the drop zone in the **Documents & Images** workspace to add pictures and PDFs, or **Find a picture** to search by describing what you remember ("the whiteboard with the migration plan"). Agents on your computer use the `remember_media` and `remember_document` tools; recall results that came from a picture carry a `media` block, and `get_media` fetches the picture.

| What | Limit |
|---|---|
| Picture formats | PNG, JPEG, GIF (first frame) and WebP |
| One picture | 25 MB from a file or the dashboard |
| One PDF | 100 MB (change with `SLM_DOC_MAX_MB`) and 500 pages. A longer PDF is refused as a whole, not cut short. |
| Library | 2 GB of pictures and PDFs per profile |

A PDF that cannot be finished (password-protected, too many pages, a page that takes too long) is marked as not finished with the reason in plain words. Pages read before it stopped stay in your memory, and dropping the same file again, or **Try again**, retries it.

## Folders and Obsidian vaults

A folder can be connected as a read-only source, and it may include pictures and PDFs:

```bash
slm sources add ~/Documents/notes      # checks the folder, shows what would be read, asks first
slm sources list
slm sources report <id>                # what was skipped, held back or failed
slm sources rescan <id>
slm sources remove <id> --purge        # disconnect, and erase the memories it gave
```

Files found while pictures and documents were off are listed as skipped and are read on the next scan once the feature is ready. You can also use **Choose folder** in the dashboard.

## Web apps

A web app connected through Web access can save a picture or PDF by asking SLM for a one-time upload link. You open the link and choose the file; it goes to your computer through the connection gateway, which keeps no copy. A link belongs to the app that asked for it, works once and expires in 10 minutes. See [[Connect Web Apps]]. Pictures and PDFs saved before 4.1.25 are held back from web apps until their text is re-checked, which SLM does in the background; they stay fully searchable on your computer.

## Housekeeping and removal

```bash
slm media gc              # report picture records whose memory is gone, and stray files
slm media gc --apply      # fix them (never deletes a memory, never touches SLM's databases)
slm media repair          # make pictures findable by what they show (re-embeds them)
slm media disable         # turn off; memories are kept
slm media disable --remove-files   # also delete the downloaded models
```

Local backups keep picture and PDF originals; cloud backups never upload them ([[Backup and Restore]]). Erasing a person or a memory reaches the stored picture and PDF files too.

The full list of limits, including the memory caps for the picture reader, is in [docs/pictures-and-documents.md](https://github.com/qualixar/superlocalmemory/blob/main/docs/pictures-and-documents.md).
