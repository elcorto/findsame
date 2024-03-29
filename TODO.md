symlinks
--------
Currently, we skip them .. need to find a way to compare them. Following the
links is not an option since that fails if the link is dead (target doesn't
exist anymore). In that case, we still want to be able to compare dirs which
have links. One option would be to treat them as a file with a one-line content
which is the link target's name or a combination of link name and target name
in a string which we can hash, such as

    link -> target

which should be fairly unique. At least that's one deterministic way to treat
links.

stdout/stderr
-------------
Use logging module.

imports
-------
Use package-local relative imports

dirs with only empty files
--------------------------
All dirs with the same number of empty files have the same hash, i.e. the hash
over N times the hash of the empty file. Since empty files are kind of a
special case, this may be considered odd. In this case we could only check the
file names to update the empty files' hashes and make them different such that
they don't get reported.
