# Source Tree
```
myfav-coworker/
├── README.md                  # Project overview and setup instructions
├── template.yaml              # AWS SAM template defining all cloud resources (IaC)
├── src/                       # Main application source code
│   ├── app.py                 # API Gateway -> Lambda handler
│   ├── worker.py              # SQS -> Lambda handler
│   ├── api/
│   ├── services/
│   ├── models/
│   └── utils/
├── tests/
│   ├── unit/
│   └── integration/
└── requirements.txt           # Python package dependencies
```

---