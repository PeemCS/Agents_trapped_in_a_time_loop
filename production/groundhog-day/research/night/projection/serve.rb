#!/usr/bin/env ruby
# A loopback screening server for immutable rehearsal media and active local archives.
require 'webrick'

class ScreeningFiles < WEBrick::HTTPServlet::FileHandler
  def service(request, response)
    # Chrome can seek using both Range and a freshness validator. The archived movie
    # bytes should be returned on every seek, including repeated open-and-close tests.
    request.header.delete('if-modified-since')
    request.header.delete('if-none-match')
    response['Cache-Control'] = 'no-store, max-age=0'
    super
  end
end

report_mode = ARGV[1] == '--report'
root = File.expand_path(report_mode ? '../../..' : '..', __dir__)
port = Integer(ARGV.fetch(0, '8765'))
server = WEBrick::HTTPServer.new(Port: port, BindAddress: '127.0.0.1',
                                 DocumentRoot: root, AccessLog: [],
                                 Logger: WEBrick::Log.new($stderr, WEBrick::Log::WARN))
server.mount('/', ScreeningFiles, root, FancyIndexing: false)
%w[INT TERM].each { |name| trap(name) { server.shutdown } }
server.start
