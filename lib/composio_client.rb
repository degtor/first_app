require 'httparty'

class ComposioClient
  include HTTParty

  BASE_URL = 'https://backend.composio.dev/api/v1'.freeze

  base_uri BASE_URL

  def initialize(api_key = ENV['COMPOSIO_API_KEY'])
    @api_key = api_key
    @headers = {
      'x-api-key' => @api_key,
      'Content-Type' => 'application/json'
    }
  end

  def get_tools(app_name)
    self.class.get("/actions", headers: @headers, query: { appNames: app_name })
  end

  def execute_action(action_name, params = {})
    self.class.post(
      "/actions/execute/#{action_name}",
      headers: @headers,
      body: params.to_json
    )
  end

  def list_connected_accounts
    self.class.get("/connectedAccounts", headers: @headers)
  end
end
