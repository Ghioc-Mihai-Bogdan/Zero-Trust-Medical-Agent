FROM nginx:alpine
# Copy the compiled Angular app into Nginx's web folder
COPY dist/clinical-mesh-ui/browser /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]