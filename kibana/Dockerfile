# Base image for Kibana (use a specific version or latest)
FROM docker.elastic.co/kibana/kibana:8.0.0

# Set environment variables (if necessary)
ENV ELASTICSEARCH_HOST=http://elasticsearch-master:9200

# Expose the Kibana port
EXPOSE 5601

# Command to start Kibana
CMD ["/usr/share/kibana/bin/kibana"]