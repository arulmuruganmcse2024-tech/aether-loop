FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04
WORKDIR /workspace
COPY train_smolvla.sh /workspace/train_smolvla.sh
RUN chmod +x /workspace/train_smolvla.sh
ENTRYPOINT ["/workspace/train_smolvla.sh"]

