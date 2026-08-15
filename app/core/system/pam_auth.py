import pam
import pwd
from fastapi.concurrency import run_in_threadpool
from fastapi import HTTPException, status

from app.core.errors import InvalidCredentialsError

def _sync_pam_uid_lookup(username: str, password: str) -> int:
    p = pam.pam()
    if p.authenticate(username, password):
        try:
            return pwd.getpwnam(username).pw_uid
        except KeyError:
            return -1
    return -1

async def get_authenticated_uid(username: str, password: str) -> int:
    uid = await run_in_threadpool(_sync_pam_uid_lookup, username, password)

    if uid == -1:
        raise InvalidCredentialsError()

    return uid