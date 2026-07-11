output "api_endpoint" {
  description = "Endpoint base da HTTP API"
  value       = aws_apigatewayv2_api.http.api_endpoint
}

output "auth_url_homolog" {
  description = "URL do POST /auth no stage homolog"
  value       = "${aws_apigatewayv2_api.http.api_endpoint}/homolog/auth"
}

output "auth_url_prod" {
  description = "URL do POST /auth no stage prod"
  value       = "${aws_apigatewayv2_api.http.api_endpoint}/prod/auth"
}
