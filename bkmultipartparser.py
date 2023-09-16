#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask_api import exceptions
from flask_api.parsers import BaseParser
from io import BytesIO
from werkzeug.formparser import MultiPartParser as WerkzeugMultiPartParser
from werkzeug.formparser import default_stream_factory

class BKMultipartParser(BaseParser):
	"""
		This multipart/form-data parser fix wrong iOS request
	"""
	media_type = 'multipart/form-data'
	handles_file_uploads = True
	handles_form_data = True

	def parse(self, data, media_type, **options):
		multipart_parser = WerkzeugMultiPartParser(default_stream_factory)

		# TODO: dirty code
		boundary = media_type.split('boundary=')[-1].strip()
		#boundary = media_type.params.get('boundary')
		if boundary is None:
			msg = 'Multipart message missing boundary in Content-Type header'
			raise exceptions.ParseError(msg)
		boundary = boundary.encode('utf-8')

		content_length = options.get('content_length')
		assert content_length is not None, 'MultiPartParser.parse() requires `content_length` argument'

		if data.rstrip()[-2:] != b"--":
			data = data.rstrip() + b"--\r\n"
		try:
			return multipart_parser.parse(BytesIO(data), boundary, len(data))
		except ValueError as exc:
			msg = f'Multipart parse error - {str(exc)}'
			raise exceptions.ParseError(msg)
