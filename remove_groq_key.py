from git_filter_repo import FilterRepo

def remove_secret(content):
    if content is None:
        return None

    lines = content.decode("utf-8").splitlines()
    cleaned = []

    for line in lines:
        # Remove any line containing Groq API keys
        if "***REMOVED***" in line:
            continue
        cleaned.append(line)

    return ("\n".join(cleaned) + "\n").encode("utf-8")

def blob_callback(blob, metadata):
    blob.data = remove_secret(blob.data)

FilterRepo(blob_callback=blob_callback).run()
