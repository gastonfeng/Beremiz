#!/usr/bin/env python
# -*- coding: utf-8 -*-

# See COPYING file for copyrights details.

# from __future__ import absolute_import
import hashlib


class ConnectorBase(object):

    chuncksize = 1024*1024

    async def BlobFromFile(self, filepath, seed):
        s = hashlib.new('md5')
        s.update(seed.encode())
        blobID = await self.SeedBlob(seed)
        with open(filepath, "rb") as f:
            sd = s.hexdigest()
            while blobID == sd:
                chunk = f.read(self.chuncksize)
                if len(chunk) == 0:
                    return blobID
                blobID = await self.AppendChunkToBlob(chunk, blobID)
                s.update(chunk)
                sd = s.hexdigest()
        raise IOError("Data corrupted during transfer or connection lost")
