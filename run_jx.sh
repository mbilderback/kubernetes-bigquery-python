jx create cluster gke \
--cluster-name='mbzd-jnknsx-tst' \
--default-admin-password='Daemon5' \
--enhanced-apis=true \
--enhanced-scopes=true \
--gitops=true \
--kaniko=true \
--ng=true \
--no-tiller=true \
--preemptible=true \
--project-id='atos-ohc-bigdata-demos' \
--prow=true \
--skip-login=true \
--tekton=true \
--vault=true \
--zone='us-west2-a'
