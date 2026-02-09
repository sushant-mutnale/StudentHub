import React, { useState, useEffect } from 'react';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import { pipelineService } from '../services/pipelineService';
import { applicationService } from '../services/applicationService';
import { jobService } from '../services/jobService';
import { FaUser, FaEllipsisV, FaBriefcase, FaCalendarAlt, FaEnvelope } from 'react-icons/fa';
import '../App.css';

const ApplicationPipeline = () => {
               const [pipeline, setPipeline] = useState(null);
               const [stages, setStages] = useState([]);
               const [jobs, setJobs] = useState([]);
               const [selectedJobId, setSelectedJobId] = useState(null);
               const [loading, setLoading] = useState(true);

               useEffect(() => {
                              loadInitialData();
               }, []);

               useEffect(() => {
                              if (selectedJobId && pipeline) {
                                             loadBoard(pipeline._id, selectedJobId);
                              }
               }, [selectedJobId, pipeline]);

               const loadInitialData = async () => {
                              try {
                                             // 1. Load Active Pipeline
                                             const activePipeline = await pipelineService.getActivePipeline();
                                             setPipeline(activePipeline);

                                             // 2. Load Active Jobs
                                             const myJobs = await jobService.getMyJobs();
                                             setJobs(myJobs);

                                             if (myJobs.length > 0) {
                                                            setSelectedJobId(myJobs[0].id);
                                             } else {
                                                            setLoading(false);
                                             }
                              } catch (error) {
                                             console.error("Failed to load pipeline data", error);
                                             setLoading(false);
                              }
               };

               const loadBoard = async (pipelineId, jobId) => {
                              setLoading(true);
                              try {
                                             const boardData = await pipelineService.getPipelineBoard(pipelineId, jobId);
                                             setStages(boardData.columns);
                              } catch (error) {
                                             console.error("Failed to load board", error);
                              } finally {
                                             setLoading(false);
                              }
               };

               const onDragEnd = async (result) => {
                              const { source, destination, draggableId } = result;

                              if (!destination) return;
                              if (source.droppableId === destination.droppableId && source.index === destination.index) return;

                              // Optimistic UI Update
                              const sourceStage = stages.find(s => s.id === source.droppableId);
                              const destStage = stages.find(s => s.id === destination.droppableId);
                              const movedCandidate = sourceStage.candidates.find(c => c.id === draggableId);

                              // Remove from source
                              sourceStage.candidates.splice(source.index, 1);
                              // Add to destination
                              destStage.candidates.splice(destination.index, 0, movedCandidate);

                              setStages([...stages]); // Trigger render

                              // API Call
                              try {
                                             await applicationService.moveStage(movedCandidate.application_id, destStage.id);
                              } catch (error) {
                                             console.error("Failed to move candidate", error);
                                             loadBoard(pipeline._id, selectedJobId); // Revert on error
                              }
               };

               // Color helpers
               const getStageColor = (name) => {
                              const lower = name.toLowerCase();
                              if (lower.includes('screen') || lower.includes('applied')) return 'border-t-4 border-blue-500';
                              if (lower.includes('interview')) return 'border-t-4 border-purple-500';
                              if (lower.includes('pending')) return 'border-t-4 border-yellow-500';
                              if (lower.includes('offer')) return 'border-t-4 border-green-500';
                              if (lower.includes('reject')) return 'border-t-4 border-red-500';
                              return 'border-t-4 border-gray-500';
               };

               if (loading && !pipeline) return (
                              <div className="flex items-center justify-center h-full">
                                             <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
                              </div>
               );
               if (!pipeline) return <div className="p-8 text-center text-gray-500">No active pipeline found.</div>;
               if (jobs.length === 0) return <div className="p-8 text-center text-gray-500">No jobs found. Post a job to see the candidate pipeline.</div>;

               return (
                              <div className="h-full flex flex-col bg-gray-50 overflow-hidden animate-fade-in">
                                             {/* Header */}
                                             <div className="p-4 border-b bg-white shadow-sm flex justify-between items-center z-10 relative">
                                                            <div className="flex items-center gap-6">
                                                                           <h2 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">
                                                                                          {pipeline.name}
                                                                           </h2>

                                                                           <div className="flex items-center bg-gray-50 border border-gray-200 rounded-lg px-3 py-1.5 transition-all hover:border-blue-300">
                                                                                          <FaBriefcase className="text-blue-500 mr-2" />
                                                                                          <select
                                                                                                         className="bg-transparent border-none text-sm font-medium text-gray-700 focus:ring-0 cursor-pointer outline-none"
                                                                                                         value={selectedJobId}
                                                                                                         onChange={(e) => setSelectedJobId(e.target.value)}
                                                                                          >
                                                                                                         {jobs.map(job => (
                                                                                                                        <option key={job.id} value={job.id}>{job.title}</option>
                                                                                                         ))}
                                                                                          </select>
                                                                           </div>
                                                            </div>
                                                            <div className="text-sm text-gray-500 flex items-center gap-2">
                                                                           <span className="flex h-2 w-2 rounded-full bg-green-500"></span>
                                                                           Live Pipeline
                                                            </div>
                                             </div>

                                             {/* Kanban Board */}
                                             <div className="flex-1 overflow-x-auto p-6 bg-gradient-to-br from-gray-50 to-blue-50">
                                                            <DragDropContext onDragEnd={onDragEnd}>
                                                                           <div className="flex h-full gap-6">
                                                                                          {stages.map((stage, index) => (
                                                                                                         <Droppable key={stage.id} droppableId={stage.id}>
                                                                                                                        {(provided, snapshot) => (
                                                                                                                                       <div
                                                                                                                                                      ref={provided.innerRef}
                                                                                                                                                      {...provided.droppableProps}
                                                                                                                                                      className={`w-80 flex-shrink-0 flex flex-col bg-gray-100/50 rounded-xl max-h-full transition-colors ${snapshot.isDraggingOver ? 'bg-blue-50ring-2 ring-blue-200' : ''
                                                                                                                                                                     }`}
                                                                                                                                                      style={{
                                                                                                                                                                     animation: `fadeIn 0.5s ease-out ${index * 0.1}s backwards`
                                                                                                                                                      }}
                                                                                                                                       >
                                                                                                                                                      {/* Column Header */}
                                                                                                                                                      <div className={`p-4 font-semibold text-gray-700 bg-white rounded-t-xl shadow-sm flex justify-between items-center ${getStageColor(stage.name)}`}>
                                                                                                                                                                     <span className="uppercase text-xs tracking-wider text-gray-500">{stage.name}</span>
                                                                                                                                                                     <span className="bg-gray-100 px-2.5 py-0.5 rounded-full text-xs font-bold text-gray-600 shadow-inner">
                                                                                                                                                                                    {stage.candidates.length}
                                                                                                                                                                     </span>
                                                                                                                                                      </div>

                                                                                                                                                      {/* Column Content */}
                                                                                                                                                      <div className="p-3 flex-1 overflow-y-auto custom-scrollbar">
                                                                                                                                                                     {stages.length > 0 && stage.candidates.map((candidate, index) => (
                                                                                                                                                                                    <Draggable
                                                                                                                                                                                                   key={candidate.id}
                                                                                                                                                                                                   draggableId={candidate.id}
                                                                                                                                                                                                   index={index}
                                                                                                                                                                                    >
                                                                                                                                                                                                   {(provided, snapshot) => (
                                                                                                                                                                                                                  <div
                                                                                                                                                                                                                                 ref={provided.innerRef}
                                                                                                                                                                                                                                 {...provided.draggableProps}
                                                                                                                                                                                                                                 {...provided.dragHandleProps}
                                                                                                                                                                                                                                 className={`bg-white p-4 mb-3 rounded-lg border border-gray-100 group hover:border-blue-200 transition-all ${snapshot.isDragging
                                                                                                                                                                                                                                                               ? 'shadow-lg ring-2 ring-blue-400 rotate-2'
                                                                                                                                                                                                                                                               : 'shadow-sm hover:shadow-md hover:-translate-y-1'
                                                                                                                                                                                                                                                }`}
                                                                                                                                                                                                                                 style={{
                                                                                                                                                                                                                                                ...provided.draggableProps.style,
                                                                                                                                                                                                                                 }}
                                                                                                                                                                                                                  >
                                                                                                                                                                                                                                 <div className="flex justify-between items-start mb-3">
                                                                                                                                                                                                                                                <div className="flex items-center gap-3">
                                                                                                                                                                                                                                                               <div className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-100 to-indigo-100 text-blue-600 flex items-center justify-center font-bold text-xs">
                                                                                                                                                                                                                                                                              {candidate.student_name.charAt(0)}
                                                                                                                                                                                                                                                               </div>
                                                                                                                                                                                                                                                               <div>
                                                                                                                                                                                                                                                                              <h4 className="font-semibold text-gray-800 text-sm">{candidate.student_name}</h4>
                                                                                                                                                                                                                                                                              {candidate.email && <div className="text-xs text-gray-400 flex items-center gap-1"><FaEnvelope size={10} />{candidate.email}</div>}
                                                                                                                                                                                                                                                               </div>
                                                                                                                                                                                                                                                </div>
                                                                                                                                                                                                                                                <button className="text-gray-300 hover:text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity">
                                                                                                                                                                                                                                                               <FaEllipsisV size={12} />
                                                                                                                                                                                                                                                </button>
                                                                                                                                                                                                                                 </div>

                                                                                                                                                                                                                                 <div className="flex flex-col gap-2 mb-3">
                                                                                                                                                                                                                                                <div className="text-xs text-gray-500 bg-gray-50 p-1.5 rounded flex items-center gap-2">
                                                                                                                                                                                                                                                               <FaCalendarAlt className="text-gray-400" />
                                                                                                                                                                                                                                                               Applied: {new Date(candidate.applied_at).toLocaleDateString()}
                                                                                                                                                                                                                                                </div>
                                                                                                                                                                                                                                 </div>

                                                                                                                                                                                                                                 <div className="border-t border-gray-50 pt-3 flex justify-between items-center">
                                                                                                                                                                                                                                                {candidate.overall_score ? (
                                                                                                                                                                                                                                                               <div className={`flex items-center text-xs font-semibold px-2 py-1 rounded-full ${candidate.overall_score >= 80 ? 'bg-green-100 text-green-700' :
                                                                                                                                                                                                                                                                                             candidate.overall_score >= 60 ? 'bg-yellow-100 text-yellow-700' :
                                                                                                                                                                                                                                                                                                            'bg-red-100 text-red-700'
                                                                                                                                                                                                                                                                              }`}>
                                                                                                                                                                                                                                                                              <FaUser className="mr-1.5" size={10} />
                                                                                                                                                                                                                                                                              {candidate.overall_score}% Match
                                                                                                                                                                                                                                                               </div>
                                                                                                                                                                                                                                                ) : (
                                                                                                                                                                                                                                                               <span className="text-xs text-gray-400 italic">Pending Score</span>
                                                                                                                                                                                                                                                )}

                                                                                                                                                                                                                                                <div className="text-xs text-blue-600 font-medium cursor-pointer hover:underline">
                                                                                                                                                                                                                                                               View Profile
                                                                                                                                                                                                                                                </div>
                                                                                                                                                                                                                                 </div>
                                                                                                                                                                                                                  </div>
                                                                                                                                                                                                   )}
                                                                                                                                                                                    </Draggable>
                                                                                                                                                                     ))}
                                                                                                                                                                     {provided.placeholder}
                                                                                                                                                      </div>
                                                                                                                                       </div>
                                                                                                                        )}
                                                                                                         </Droppable>
                                                                                          ))}
                                                                           </div>
                                                            </DragDropContext>
                                             </div>
                              </div>
               );
};

export default ApplicationPipeline;
