## Current Status

Student-submitted code questions are part of the course material for the 6.00x series, 6.86, and 7.8QBWx courses. These are automatically evaluated and graded in the context of the edX interface. The current implementation of this feature relies on the combination of [xqueue](https://github.com/openedx/xqueue) and [xqueue-watcher](https://github.com/openedx/xqueue-watcher). The xqueue and xqueue-watcher applications are [deprecated](https://github.com/openedx/public-engineering/issues/214) and slated for removal from the Open edX ecosystem in October 2024\.

The user experience for course teams and students is quite poor. Course teams have no reliable means of validating their grader tests without deploying them to a running environment, leading to longer cycle times and a lack of visibility into errors. This also contributes to a substantial support burden on engineering to provide debugging information and onboarding for deployment. Students get opaque responses when their submissions are invalid or incorrect. Instructors have limited visibility into the code that their students are submitting and no ability to provide in-context feedback to the students.

As an alternative to the combination of xqueue and xqueue-watcher, there are several paid services that offer automatic grading of student code. These platforms also offer many additional features beyond the capabilities of xqueue/xqueue-watcher. Examples include in-browser editor support (e.g., Visual Studio Code), in-context feedback mechanisms for instructors to comment on student code, and workspace management for students and instructors to keep track of what code has been written. A non-exhaustive list of companies providing this service includes [Codio](https://www.codio.com/), [Vocareum](https://www.vocareum.com/), and [CodeGrade](https://www.codegrade.com/).

The core capability of the xqueue-watcher code grading system is to facilitate a request/response interaction for evaluating student-submitted code in a stateless manner. This is a benefit in that it allows for scaling to a large number of students. If there is a desire to have a more stateful experience for the learners, then instructors are advised to take advantage of services as noted above.

## Planned Improvements

In order to provide continuity of service to course teams currently using code grading in their classes, the engineering team will continue to provide the xqueue/xqueue-watcher systems as a service for Open edX courses. This will require investing engineering resources to upgrade the current code to be compatible with newer versions of the edX platform, as well as updating the system dependencies. The deployment architecture will also require upgrades to be compatible with the Open Learning infrastructure platform.

## Scope Of Work

The focus of the improvements and upgrades to xqueue and xqueue-watcher will be on the local development experience for course instructors, and reducing the maintenance burden on infrastructure engineers. 

### Upgrade Service Deployment

The initial scope of work will be focused on migrating the deployment of the xqueue-watcher service. This will include the ability to more easily scale capacity, allowing for the migration of current grader workloads hosted by edx.org/2U onto our infrastructure.This will require the dedicated attention of one member of the infrastructure engineering team for approximately 2 months to accomplish.

### Enable Local Testing

A significant source of frustration with the xqueue-watcher system is the inability to effectively test the functionality of the evaluation functions during their development. In addition, the course teams have no control over the runtime environment and system dependencies available to the student code. The current state of the service is that course teams are only able to use Python code and there is no means of specifying which version of the language to use.

In order to make this easier, a new execution context that uses Docker images will be added to the xqueue-watcher service. This will allow course teams to develop their own images, specify the language and version that students can write their code in, and specify the dependencies available to them. Having a pre-built image to use for run-time execution also reduces the work required of the infrastructure team, allowing them to focus on the runtime of the core service rather than being responsible for the evaluation context of student code.

For course teams that have existing grader logic, the engineering team will assist them in the initial creation of a Docker image that is compatible with their current code. This will not require substantial modifications to the grader code as it is presently written in order to function under the new execution context.

The work to add and validate this functionality will require the attention of 2 engineers for approximately 4 months.

### Provide Debugging Information To Course Teams

The other major source of friction for both course instructors and platform operators is the inability to debug issues that students encounter. To allow course teams to diagnose and debug errors, the infrastructure team will collect log messages emitted by the grader into a system that allows for searching of that data. Course teams will be granted access to their logs for the purpose of supporting their students in the event that there are logical or resource-related failures due to student submissions and/or grader logic. This will require the focus of 1 infrastructure engineer for approximately 1 month to configure, integrate, and validate the functionality and permission scoping. If there is a desire to integrate this experience into the Open edX interface then it will require an additional developer for approximately 1 \- 2 months.

### Ongoing Maintenance, Support, and Improvements

To support the ongoing operation and support of the automated grader service will require the attention of 1 full time DevOps engineer. The responsibilities of this engineer include:

* Helping course teams with deployment and debugging of their graders  
* Build utilities to simplify the creation of graders by course teams  
* Perform ongoing maintenance and upgrades of the xqueue and xqueue-watcher projects  
* Manage deployment, monitoring, and scaling of the automated graders

## Explicitly Out Of Scope

There are a number of features that we are explicitly not going to offer to course teams. In particular, we have no intention of adding features around dedicated lab spaces for students, editor integrations, or support for other courseware systems. For any use cases that go beyond a simple request/response interchange for evaluating student code the course team is advised to engage with services such as Codio, CodeGrade, etc. as noted above.

## Estimated Costs

As noted in the scope of work, the ongoing support, maintenance, and upgrades of the service will require an additional dedicated DevOps engineer.

The infrastructure costs for the current installation of xqueue-watchers is approximately $700/month. With increased scaling to account for the course load currently being managed on edx.org that number is anticipated to reach \~$1,500/month.

The total estimated cost per learner is \~$5/learner/month. This is based on the above costs and an enrollment rate of \~3,700 verified learners per course term.

## Comparison To Alternatives

| Property | Xqueue/Xqueue-Watcher | Cod.io |
| :---- | :---- | :---- |
| Cost | \~$5/student/month | \~$12/student/month minimum |
| Compatibility | Open edX only | Open edX, Canvas, any LMS that supports LTI |
| Features | Automated evaluation of student code submissions | In-browser IDE, Automated code evaluation, Cloud lab environments, Content authoring |
| Instructor Support | Business hours by staff FTE | [Assistance with development and maintenance of problems and graders](https://docs.codio.com/index.html) |
| Student Support | 24/7 2U or MITx Online escalated to course team | [https://docs.codio.com/student.html](https://docs.codio.com/student.html) |

